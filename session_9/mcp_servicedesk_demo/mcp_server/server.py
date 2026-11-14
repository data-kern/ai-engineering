"""The KernMart IT service desk, as an MCP server.

Eleven tools. Any MCP client can discover and call them: our agent, Claude Desktop, an IDE, a test script.
The tool code is written ONCE, here. No agent contains a copy of it.

Run it on your laptop (stdio: a client starts it as a child process):
    EMPLOYEE_ID=E-1001 python mcp_server/server.py

Run it as a network service (this is how it runs in Docker and Kubernetes):
    python mcp_server/server.py --http          # http://127.0.0.1:8000/mcp

How to read this file:
    1. create the server        FastMCP(...)
    2. define a tool            a normal Python function + @mcp.tool(...)
    3. the model reads          the function NAME, the DOCSTRING and the TYPE HINTS. They become the tool's schema.
    4. identity                 ctx + who_is_asking(): the employee is never an argument
"""
import os
import sys
from typing import Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))     # so `servicedesk_core` is found when run as a script

from mcp_server.ops import governed, start_tracing, who_is_asking     # noqa: E402
from servicedesk_core import db, desk                                  # noqa: E402

# ---- 1. create the server -------------------------------------------------------------------
mcp = FastMCP(
    "kernmart-servicedesk",
    instructions="IT service desk tools for KernMart employees. Every tool acts for the signed-in employee only.",
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
    stateless_http=True,      # no session kept in the server's memory: any replica can answer any request
    json_response=True,       # plain JSON replies, friendly to load balancers and gateways
    log_level=os.getenv("MCP_LOG_LEVEL", "WARNING"),     # quiet in a student's terminal; Compose and Kubernetes set INFO
)

# Hints for clients. They are hints, not security: the real limits are in servicedesk_core/desk.py.
READ_ONLY = ToolAnnotations(readOnlyHint=True)
WRITES_SAFELY = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
WRITES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)

Category = Literal["access", "network", "software", "hardware", "email", "security", "other"]
Urgency = Literal["low", "normal", "high", "critical"]


# ---- 2. define tools -----------------------------------------------------------------------
# A tool is a function. The decorator registers it; @governed adds the audit row and the Phoenix trace span.
@mcp.tool(annotations=READ_ONLY)
@governed
def search_knowledge_base(query: str, ctx: Context) -> dict:
    """Search the IT knowledge base. Use it FIRST for any how-to question or problem.

    Returns up to 3 articles with their full steps. If nothing relevant comes back, say so
    honestly and escalate: do not invent steps.

    Args:
        query: What the employee needs, in a few plain words. Example: "vpn keeps disconnecting".
    """
    return desk.search_knowledge_base(query)


@mcp.tool(annotations=READ_ONLY)
@governed
def get_account_status(ctx: Context) -> dict:
    """Check the signed-in employee's account: locked or active, failed sign-in attempts,
    whether the security team has put a hold on it, and whether MFA is set up."""
    return desk.get_account_status(who_is_asking(ctx))


@mcp.tool(annotations=WRITES_SAFELY)
@governed
def unlock_account(ctx: Context) -> dict:
    """Unlock the signed-in employee's locked account.

    The rules are enforced by the system, not by you: it refuses when the security team has put a
    hold on the account, and after 3 unlocks in 24 hours. If it refuses, follow its `what_to_do`.
    """
    return desk.unlock_account(who_is_asking(ctx))


@mcp.tool(annotations=WRITES)
@governed
def send_password_reset_link(ctx: Context) -> dict:
    """Email a password reset link to the address ON FILE for the signed-in employee.

    You cannot choose the address and you never see the link. Use it when the employee forgot
    their password. Never ask the employee for a password.
    """
    return desk.send_password_reset_link(who_is_asking(ctx))


@mcp.tool(annotations=READ_ONLY)
@governed
def list_software_catalog(ctx: Context) -> dict:
    """List the software that can be requested, which items are self-service, and how many seats are free."""
    return desk.list_software_catalog()


@mcp.tool(annotations=WRITES_SAFELY)
@governed
def request_software_license(software: str, ctx: Context) -> dict:
    """Assign a software seat to the signed-in employee. Works only for self-service apps with a free seat.

    Args:
        software: The exact name from list_software_catalog, for example "Figma".
    """
    return desk.request_software_license(who_is_asking(ctx), software)


@mcp.tool(annotations=WRITES)
@governed
def create_ticket(summary: str, details: str, category: Category, ctx: Context) -> dict:
    """Open a ticket for the employee's problem. Do this once per problem, before you act on it.

    Args:
        summary: One line, for example "VPN keeps disconnecting".
        details: What the employee said and what you found so far. A human may read only this.
        category: The area of the problem.
    """
    return desk.create_ticket(who_is_asking(ctx), summary, details, category)


@mcp.tool(annotations=READ_ONLY)
@governed
def get_ticket_status(ticket_id: str, ctx: Context) -> dict:
    """Show the status of one of the employee's tickets, including replies from the service desk team.

    Args:
        ticket_id: For example "IT-1004".
    """
    return desk.get_ticket_status(who_is_asking(ctx), ticket_id)


@mcp.tool(annotations=READ_ONLY)
@governed
def list_my_tickets(ctx: Context) -> dict:
    """List the signed-in employee's 10 most recent tickets with their status."""
    return desk.list_tickets(who_is_asking(ctx))


@mcp.tool(annotations=WRITES_SAFELY)
@governed
def close_ticket_as_resolved(ticket_id: str, resolution: str, ctx: Context) -> dict:
    """Close a ticket you SOLVED. Only after the fix worked or the knowledge base fully answered the question.

    Args:
        ticket_id: The ticket you opened for this problem.
        resolution: What fixed it, in one or two sentences.
    """
    return desk.close_ticket(who_is_asking(ctx), ticket_id, resolution)


@mcp.tool(annotations=WRITES_SAFELY)
@governed
def escalate_to_human(ticket_id: str, reason: str, urgency: Urgency, ctx: Context) -> dict:
    """Hand a ticket to a human service desk colleague, who is alerted by email and Slack.

    Use it when: the knowledge base has no answer, a tool refused and told you to escalate, the
    employee asks for a person, or it is a security incident or a lost device.

    Args:
        ticket_id: The ticket you opened for this problem.
        reason: Why you cannot solve it. A human reads this first, so be specific.
        urgency: critical = security incident or lost device. high = employee cannot work at all.
            normal = default. low = can wait for the next working day.
    """
    return desk.escalate_ticket(who_is_asking(ctx), ticket_id, reason, urgency)


# ---- operations endpoints (plain HTTP next to the MCP endpoint) ------------------------------
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> Response:
    """Kubernetes calls this to decide whether to send traffic to this replica."""
    if db.is_reachable():
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "database_unreachable"}, status_code=503)


# ---- run it ------------------------------------------------------------------------------------
if __name__ == "__main__":
    use_http = "--http" in sys.argv
    print(start_tracing(), file=sys.stderr)       # stderr: on stdio, stdout belongs to the protocol
    if use_http:
        db.wait_until_reachable()
    mcp.run(transport="streamable-http" if use_http else "stdio")
