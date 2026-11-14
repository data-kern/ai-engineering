"""The IT service desk's business rules, as plain Python functions.

Everything the agent can do ends up here, whether it arrives through an MCP server or through a
function tool written inside an agent. The rules live in THIS file, in code, not in a prompt:

  * a locked account is unlocked at most 3 times per day, and never when security put a hold on it
  * a password reset link is only ever emailed to the address on file
  * a software seat is only handed out if the app is self-service and a seat is free
  * an employee can only see and change their own tickets

How the functions answer:
  * rule says no        -> {"done": False, "reason": ..., "what_to_do": ...}   (a normal answer, the agent adapts)
  * rule says yes       -> {"done": True, ...}
  * caller made a mistake (unknown ticket, someone else's ticket) -> raise DeskError
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from . import db, notify

ACTIONS_PER_DAY = 3
RESET_LINK_MINUTES = 30
RESET_BASE_URL = "https://sso.kernmart.example/reset"

CATEGORIES = ("access", "network", "software", "hardware", "email", "security", "other")
URGENCIES = ("low", "normal", "high", "critical")
RESPONSE_TIME = {
    "critical": "within 15 minutes",
    "high": "within 1 hour",
    "normal": "within 4 working hours",
    "low": "by the next working day",
}


class DeskError(Exception):
    """The request itself was wrong. The message is safe to show to the model."""


# --------------------------------------------------------------------------------------
# People and accounts
# --------------------------------------------------------------------------------------
def get_employee(employee_id):
    employee = db.query_one("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    if employee is None:
        raise DeskError(f"Unknown employee '{employee_id}'.")
    return employee


def get_account_status(employee_id):
    get_employee(employee_id)
    account = db.query_one(
        "SELECT status, failed_attempts, security_hold, mfa_enrolled FROM accounts WHERE employee_id = %s",
        (employee_id,),
    )
    if account is None:
        raise DeskError("This employee has no directory account.")
    return account


def _actions_in_last_day(employee_id, action):
    row = db.query_one(
        "SELECT count(*) AS n FROM account_actions "
        "WHERE employee_id = %s AND action = %s AND at > now() - interval '1 day'",
        (employee_id, action),
    )
    return row["n"]


def _record_action(employee_id, action):
    db.execute("INSERT INTO account_actions (employee_id, action) VALUES (%s, %s)", (employee_id, action))


def unlock_account(employee_id):
    account = get_account_status(employee_id)
    if account["security_hold"]:
        return {
            "done": False,
            "reason": "security_hold",
            "what_to_do": "Do not unlock. The security team froze this account. "
                          "Escalate to a human with urgency 'critical' and tell the employee a person will contact them.",
        }
    if account["status"] != "locked":
        return {"done": False, "reason": "not_locked", "what_to_do": "The account is not locked. Nothing to unlock."}
    if _actions_in_last_day(employee_id, "unlock") >= ACTIONS_PER_DAY:
        return {
            "done": False,
            "reason": "daily_limit_reached",
            "what_to_do": f"Already unlocked {ACTIONS_PER_DAY} times in 24 hours. Escalate to a human with urgency 'normal'.",
        }
    db.execute("UPDATE accounts SET status = 'active', failed_attempts = 0 WHERE employee_id = %s", (employee_id,))
    _record_action(employee_id, "unlock")
    return {"done": True, "message": "Account unlocked. The employee can sign in now."}


def send_password_reset_link(employee_id):
    employee = get_employee(employee_id)
    account = get_account_status(employee_id)
    if account["security_hold"]:
        return {
            "done": False,
            "reason": "security_hold",
            "what_to_do": "Do not send a reset link. Escalate to a human with urgency 'critical'.",
        }
    if _actions_in_last_day(employee_id, "reset_link") >= ACTIONS_PER_DAY:
        return {
            "done": False,
            "reason": "daily_limit_reached",
            "what_to_do": "Reset link already sent 3 times today. Escalate to a human with urgency 'normal'.",
        }

    token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_LINK_MINUTES)
    db.execute(
        "INSERT INTO reset_tokens (token_hash, employee_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash, employee_id, expires_at),
    )

    # The link goes to the address ON FILE. The model never chooses where it is sent.
    email_status = notify.send_email(
        employee["email"],
        "Your KernMart password reset link",
        f"Hello {employee['name']},\n\nUse this link within {RESET_LINK_MINUTES} minutes:\n"
        f"{RESET_BASE_URL}?token={token}\n\nIf you did not ask for this, tell the service desk.\n",
    )
    if email_status != "sent":
        return {"done": False, "reason": "email_failed",
                "what_to_do": "The email could not be sent. Escalate to a human with urgency 'normal'."}
    _record_action(employee_id, "reset_link")
    return {"done": True, "message": f"Reset link emailed to the address on file. It expires in {RESET_LINK_MINUTES} minutes."}


# --------------------------------------------------------------------------------------
# Knowledge base and software
# --------------------------------------------------------------------------------------
def search_knowledge_base(query, limit=3):
    """PostgreSQL full-text search. Any word may match (OR), best matches first."""
    words = [word for word in "".join(c if c.isalnum() else " " for c in query.lower()).split() if len(word) > 1]
    if not words:
        return {"articles": []}
    rows = db.query(
        "SELECT article_id, title, body, ts_rank_cd(search, q) AS score "
        "FROM kb_articles, to_tsquery('english', %s) AS q "
        "WHERE search @@ q ORDER BY score DESC LIMIT %s",
        (" | ".join(words), limit),
    )
    return {"articles": [{"article_id": r["article_id"], "title": r["title"], "body": r["body"]} for r in rows]}


def list_software_catalog():
    rows = db.query(
        "SELECT c.software, c.self_service, c.approval_note, "
        "       c.seats_total - count(l.employee_id) AS seats_free "
        "FROM software_catalog c LEFT JOIN software_licenses l USING (software) "
        "GROUP BY c.software ORDER BY c.software"
    )
    return {"software": rows}


def request_software_license(employee_id, software):
    get_employee(employee_id)
    with db.connect() as conn:
        item = conn.execute(
            "SELECT * FROM software_catalog WHERE lower(software) = lower(%s) FOR UPDATE", (software,)
        ).fetchone()
        if item is None:
            return {"done": False, "reason": "not_in_catalog",
                    "what_to_do": "Call list_software_catalog and pick a name from it. If the app is not listed, escalate."}
        if not item["self_service"]:
            return {"done": False, "reason": "needs_approval",
                    "what_to_do": f"{item['approval_note']} Escalate to a human with urgency 'normal'."}

        already = conn.execute(
            "SELECT 1 FROM software_licenses WHERE employee_id = %s AND software = %s",
            (employee_id, item["software"]),
        ).fetchone()
        if already:
            return {"done": True, "message": f"{item['software']} was already assigned to this employee."}

        used = conn.execute(
            "SELECT count(*) AS n FROM software_licenses WHERE software = %s", (item["software"],)
        ).fetchone()["n"]
        if used >= item["seats_total"]:
            return {"done": False, "reason": "no_seats_free",
                    "what_to_do": "All seats are taken. Escalate to a human with urgency 'low': the software asset team can buy more."}
        conn.execute(
            "INSERT INTO software_licenses (employee_id, software) VALUES (%s, %s)", (employee_id, item["software"])
        )
    return {"done": True, "message": f"A {item['software']} seat is now assigned. It appears in the Software Centre within 15 minutes."}


# --------------------------------------------------------------------------------------
# Tickets
# --------------------------------------------------------------------------------------
def create_ticket(employee_id, summary, details, category):
    get_employee(employee_id)
    if category not in CATEGORIES:
        raise DeskError(f"category must be one of {', '.join(CATEGORIES)}")
    ticket_id = db.query_one("SELECT 'IT-' || nextval('ticket_number') AS id")["id"]
    db.execute(
        "INSERT INTO tickets (ticket_id, employee_id, category, summary, details) VALUES (%s, %s, %s, %s, %s)",
        (ticket_id, employee_id, category, summary, details),
    )
    return {"done": True, "ticket_id": ticket_id, "status": "open"}


def _get_own_ticket(employee_id, ticket_id):
    ticket = db.query_one("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
    # Same message for "does not exist" and "belongs to someone else": do not reveal other people's tickets.
    if ticket is None or ticket["employee_id"] != employee_id:
        raise DeskError(f"Ticket '{ticket_id}' not found for this employee.")
    return ticket


def get_ticket_status(employee_id, ticket_id):
    ticket = _get_own_ticket(employee_id, ticket_id)
    replies = db.query(
        "SELECT author, body, at FROM ticket_replies WHERE ticket_id = %s ORDER BY id", (ticket_id,)
    )
    return {
        "ticket_id": ticket_id,
        "summary": ticket["summary"],
        "status": ticket["status"],
        "urgency": ticket["urgency"],
        "resolution": ticket["resolution"],
        "replies_from_service_desk": [
            {"from": r["author"], "message": r["body"], "at": r["at"].isoformat(timespec="minutes")} for r in replies
        ],
    }


def list_tickets(employee_id):
    get_employee(employee_id)
    rows = db.query(
        "SELECT ticket_id, summary, status, urgency FROM tickets WHERE employee_id = %s ORDER BY created_at DESC LIMIT 10",
        (employee_id,),
    )
    return {"tickets": rows}


def close_ticket(employee_id, ticket_id, resolution):
    ticket = _get_own_ticket(employee_id, ticket_id)
    if ticket["status"] != "open":
        return {"done": False, "reason": "not_open",
                "what_to_do": f"The ticket is '{ticket['status']}', so it cannot be closed by the agent."}
    db.execute(
        "UPDATE tickets SET status = 'resolved_by_agent', resolution = %s, updated_at = now() WHERE ticket_id = %s",
        (resolution, ticket_id),
    )
    return {"done": True, "ticket_id": ticket_id, "status": "resolved_by_agent"}


def escalate_ticket(employee_id, ticket_id, reason, urgency):
    if urgency not in URGENCIES:
        raise DeskError(f"urgency must be one of {', '.join(URGENCIES)}")
    ticket = _get_own_ticket(employee_id, ticket_id)
    if ticket["status"] == "escalated":
        return {"done": True, "ticket_id": ticket_id, "already_escalated": True,
                "expected_response": RESPONSE_TIME[ticket["urgency"]]}
    if ticket["status"] != "open":
        return {"done": False, "reason": "not_open", "what_to_do": f"The ticket is already '{ticket['status']}'."}

    db.execute(
        "UPDATE tickets SET status = 'escalated', urgency = %s, escalation_reason = %s, updated_at = now() "
        "WHERE ticket_id = %s",
        (urgency, reason, ticket_id),
    )
    alerts = notify.alert_service_desk(ticket, get_employee(employee_id), reason, urgency)
    # Honest answer: the ticket IS in the human queue either way, but say whether a person was pinged.
    return {
        "done": True,
        "ticket_id": ticket_id,
        "status": "escalated",
        "expected_response": RESPONSE_TIME[urgency],
        "human_alerted": alerts["any_sent"],
        "alert_channels": {"email": alerts["email"], "slack": alerts["slack"]},
    }


# --------------------------------------------------------------------------------------
# The human side (used by the staff console, never by the agent)
# --------------------------------------------------------------------------------------
def staff_list_tickets(only_escalated=True):
    where = "WHERE t.status = 'escalated'" if only_escalated else ""
    return db.query(
        "SELECT t.*, e.name AS employee_name, e.email AS employee_email "
        f"FROM tickets t JOIN employees e USING (employee_id) {where} "
        "ORDER BY CASE t.urgency WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, t.created_at"
    )


def staff_reply(ticket_id, staff_id, body, resolve):
    staff = get_employee(staff_id)
    if staff["role"] != "staff":
        raise DeskError("Only service-desk staff may reply.")
    ticket = db.query_one("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
    if ticket is None:
        raise DeskError(f"Ticket '{ticket_id}' not found.")
    db.execute("INSERT INTO ticket_replies (ticket_id, author, body) VALUES (%s, %s, %s)",
               (ticket_id, staff["name"], body))
    if resolve:
        db.execute("UPDATE tickets SET status = 'resolved_by_human', resolution = %s, updated_at = now() "
                   "WHERE ticket_id = %s", (body, ticket_id))
    employee = get_employee(ticket["employee_id"])
    email_status = notify.send_email(
        employee["email"], f"{ticket_id}: reply from the service desk",
        f"Hello {employee['name']},\n\n{body}\n\n-- {staff['name']}, KernMart IT service desk\n")
    return {"done": True, "employee_emailed": email_status}


def recent_audit(limit=50):
    rows = db.query("SELECT * FROM audit_log ORDER BY id DESC LIMIT %s", (limit,))
    for row in rows:
        row["arguments"] = json.dumps(row["arguments"])
    return rows
