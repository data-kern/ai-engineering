"""Small helper for the demo database. Not part of the agent.

    python db.py reset      drop everything and load the sample data again (do this before each scene)
    python db.py accounts   who is locked, who has a security hold
    python db.py tickets    every ticket and its status
    python db.py audit      the last 20 tool calls, written by the MCP server
    python db.py software   who holds which software seat

It talks to the same PostgreSQL as the agent: DATABASE_URL, default localhost:5433 (the Docker Compose one).
"""
import sys

from servicedesk_core import db

QUERIES = {
    "accounts": "SELECT employee_id, status, failed_attempts, security_hold FROM accounts ORDER BY 1",
    "tickets": "SELECT ticket_id, employee_id, status, urgency, summary FROM tickets ORDER BY created_at",
    "audit": "SELECT id, employee_id, tool, outcome, detail FROM (SELECT * FROM audit_log ORDER BY id DESC LIMIT 20) recent ORDER BY id",
    "software": "SELECT software, employee_id FROM software_licenses ORDER BY 1, 2",
}


def print_table(rows):
    if not rows:
        print("(no rows)")
        return
    columns = list(rows[0])
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in columns}
    print("  ".join(c.ljust(widths[c]) for c in columns))
    for row in rows:
        print("  ".join(str(row[c]).ljust(widths[c]) for c in columns))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "reset":
        db.reset()
        print("Database reset: sample employees, accounts, knowledge base and software loaded.")
    elif command in QUERIES:
        print_table(db.query(QUERIES[command]))
    else:
        sys.exit(__doc__)
