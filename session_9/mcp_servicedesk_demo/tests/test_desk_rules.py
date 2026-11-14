"""The rules in servicedesk_core/desk.py, tested against the REAL PostgreSQL (no model, no MCP).

    docker compose up -d postgres mailpit
    pytest tests/test_desk_rules.py

WARNING: every test starts by resetting the demo database, exactly like `python db.py reset`.
"""
import httpx
import pytest

from servicedesk_core import db, desk, notify

PRIYA, RAHUL, MEERA = "E-1001", "E-1002", "E-1003"      # Priya: locked. Rahul: fine. Meera: locked + security hold.


@pytest.fixture(autouse=True)
def fresh_database():
    db.reset()


def emails_in_mailpit():
    """Ask the real mail server what it received. Returns None when Mailpit is not running."""
    try:
        response = httpx.get("http://localhost:8025/api/v1/messages", timeout=2)
        return response.json()["messages"]
    except httpx.HTTPError:
        return None


def lock_account_again(employee_id):
    db.execute("UPDATE accounts SET status = 'locked' WHERE employee_id = %s", (employee_id,))


# ---- unlock ----------------------------------------------------------------------------------
def test_unlock_works_for_a_normal_locked_account():
    assert desk.unlock_account(PRIYA)["done"] is True
    assert desk.get_account_status(PRIYA)["status"] == "active"


def test_unlock_is_refused_when_security_put_a_hold_on_the_account():
    answer = desk.unlock_account(MEERA)
    assert answer["done"] is False and answer["reason"] == "security_hold"
    assert desk.get_account_status(MEERA)["status"] == "locked"          # and nothing changed
    assert "critical" in answer["what_to_do"]                           # the refusal tells the agent what to do next


def test_unlocking_an_account_that_is_not_locked_changes_nothing():
    answer = desk.unlock_account(RAHUL)
    assert answer["done"] is False and answer["reason"] == "not_locked"


def test_unlock_stops_after_three_times_in_a_day():
    for _ in range(3):
        assert desk.unlock_account(PRIYA)["done"] is True
        lock_account_again(PRIYA)
    answer = desk.unlock_account(PRIYA)
    assert answer["done"] is False and answer["reason"] == "daily_limit_reached"


# ---- password reset link ---------------------------------------------------------------------
def test_reset_link_is_emailed_only_to_the_address_on_file():
    before = emails_in_mailpit()
    if before is None:
        pytest.skip("Mailpit is not running (docker compose up -d mailpit)")
    assert desk.send_password_reset_link(RAHUL)["done"] is True
    after = emails_in_mailpit()
    new_messages = after[: len(after) - len(before) + 1]
    recipients = [to["Address"] for message in new_messages for to in message["To"]]
    assert "rahul.mehta@kernmart.example" in recipients


def test_reset_link_token_is_stored_as_a_hash_never_as_the_token():
    desk.send_password_reset_link(RAHUL)
    stored = db.query_one("SELECT token_hash FROM reset_tokens")["token_hash"]
    assert len(stored) == 64            # a SHA-256 hex digest, not a url-safe token


def test_reset_link_is_refused_during_a_security_hold():
    assert desk.send_password_reset_link(MEERA)["reason"] == "security_hold"


# ---- software --------------------------------------------------------------------------------
def test_last_figma_seat_goes_to_the_first_request_and_the_next_one_finds_none():
    assert desk.request_software_license(RAHUL, "figma")["done"] is True          # name match ignores case
    answer = desk.request_software_license(PRIYA, "Figma")
    assert answer["done"] is False and answer["reason"] == "no_seats_free"


def test_asking_twice_for_the_same_software_takes_only_one_seat():
    desk.request_software_license(RAHUL, "Zoom")
    desk.request_software_license(RAHUL, "Zoom")
    assert db.query_one("SELECT count(*) AS n FROM software_licenses WHERE software = 'Zoom'")["n"] == 1


def test_apps_that_need_manager_approval_are_never_handed_out():
    answer = desk.request_software_license(RAHUL, "Tableau")
    assert answer["done"] is False and answer["reason"] == "needs_approval"
    assert db.query_one("SELECT count(*) AS n FROM software_licenses WHERE software = 'Tableau'")["n"] == 0


# ---- tickets ---------------------------------------------------------------------------------
def test_an_employee_cannot_see_someone_elses_ticket():
    ticket_id = desk.create_ticket(PRIYA, "Printer", "offline", "hardware")["ticket_id"]
    with pytest.raises(desk.DeskError):
        desk.get_ticket_status(RAHUL, ticket_id)
    with pytest.raises(desk.DeskError):
        desk.close_ticket(RAHUL, ticket_id, "I fixed it")


def test_escalating_puts_the_ticket_in_the_human_queue_and_alerts_by_email():
    before = emails_in_mailpit()
    ticket_id = desk.create_ticket(MEERA, "Locked", "security hold", "security")["ticket_id"]
    answer = desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    assert answer["status"] == "escalated" and answer["expected_response"] == "within 15 minutes"
    assert ticket_id in [t["ticket_id"] for t in desk.staff_list_tickets()]
    if before is not None:
        assert answer["human_alerted"] is True and answer["alert_channels"]["email"] == "sent"


def test_escalating_twice_does_not_alert_twice():
    ticket_id = desk.create_ticket(MEERA, "Locked", "security hold", "security")["ticket_id"]
    desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    again = desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    assert again["already_escalated"] is True and "alert_channels" not in again


def test_the_ticket_is_escalated_even_when_no_alert_can_be_sent(monkeypatch):
    """If the mail server is down the human queue must still contain the ticket, and the answer must say so honestly."""
    monkeypatch.setattr(notify, "SMTP_PORT", 1)                         # nothing listens on port 1
    ticket_id = desk.create_ticket(MEERA, "Locked", "security hold", "security")["ticket_id"]
    answer = desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    assert answer["status"] == "escalated" and answer["human_alerted"] is False
    assert answer["alert_channels"]["email"].startswith("failed")


def test_an_agent_cannot_close_a_ticket_that_was_already_escalated():
    ticket_id = desk.create_ticket(MEERA, "Locked", "security hold", "security")["ticket_id"]
    desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    assert desk.close_ticket(MEERA, ticket_id, "all good")["reason"] == "not_open"


def test_only_staff_can_reply_and_the_employee_sees_the_reply():
    ticket_id = desk.create_ticket(MEERA, "Locked", "security hold", "security")["ticket_id"]
    desk.escalate_ticket(MEERA, ticket_id, "security hold", "critical")
    with pytest.raises(desk.DeskError):
        desk.staff_reply(ticket_id, RAHUL, "I am not staff", resolve=True)
    desk.staff_reply(ticket_id, "S-9001", "We called you.", resolve=True)
    status = desk.get_ticket_status(MEERA, ticket_id)
    assert status["status"] == "resolved_by_human"
    assert status["replies_from_service_desk"][0]["message"] == "We called you."


# ---- knowledge base --------------------------------------------------------------------------
@pytest.mark.parametrize("question, expected_article", [
    ("my vpn keeps disconnecting", "KB-001"),
    ("I got a new phone and need my authenticator moved", "KB-005"),
    ("I clicked a link in a strange email", "KB-010"),
])
def test_knowledge_base_finds_the_right_article_first(question, expected_article):
    articles = desk.search_knowledge_base(question)["articles"]
    assert articles[0]["article_id"] == expected_article


def test_knowledge_base_returns_nothing_for_nonsense():
    assert desk.search_knowledge_base("zxqv blorf")["articles"] == []
