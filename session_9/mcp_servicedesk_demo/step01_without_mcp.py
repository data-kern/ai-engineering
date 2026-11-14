"""
STEP 01: the IT service desk agent WITHOUT MCP. Every tool is written inside the agent's own file.

This is how you built agents in Sessions 7 and 8: a Python function per tool, with @function_tool.
It works. Read the file and count how much of it is tool declarations, not agent.

THE PROBLEM this step shows (it is not a bug, it is a cost):
  - The agent file contains eleven tool wrappers. Their names, docstrings and schemas live HERE.
  - A second agent (a different team, LangGraph, Claude Desktop, an IDE) cannot use them.
    It would copy all eleven wrappers, and the two copies would drift apart.
  - There is nowhere central to log, count or limit the calls.
  - Changing a tool means redeploying the agent.
  Step 02 builds the same tools as an MCP server. Step 03 deletes this whole block from the agent.

Run:  docker compose up -d postgres mailpit        (the real database and the real mail server)
      python db.py reset
      export GROQ_API_KEY=...                       (free key: https://console.groq.com)
      python step01_without_mcp.py

Try (you pick who you are when it starts):
  1. As E-1001 (Priya):  I'm locked out of my account.
  2. As E-1001:          How do I connect to the VPN?
  3. As E-1003 (Meera):  I'm locked out of my account.      (security hold: the agent must escalate, not unlock)
  4. As E-1002 (Rahul):  I need Figma.
Then:  python db.py tickets      and open http://localhost:8025 to read the emails the agent sent.

An empty line quits.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Literal

from agents import Agent, RunContextWrapper, Runner, SQLiteSession, function_tool

import llm
from agent_instructions import INSTRUCTIONS
from servicedesk_core import desk


# ---- who is asking: OUR fact, hidden from the model (same idea as Session 8, step 02) ----------------
@dataclass
class Requester:
    employee_id: str


def as_json(result):
    return json.dumps(result, default=str)


# ---- the tools: eleven wrappers around servicedesk_core.desk --------------------------------------
# @function_tool turns a function into a tool. The docstring and the type hints become what the model reads.
@function_tool
def search_knowledge_base(ctx: RunContextWrapper[Requester], query: str) -> str:
    """Search the IT knowledge base. Use it FIRST for any how-to question or problem.

    Returns up to 3 articles with their full steps. If nothing relevant comes back, say so
    honestly and escalate: do not invent steps.

    Args:
        query: What the employee needs, in a few plain words. Example: "vpn keeps disconnecting".
    """
    return as_json(desk.search_knowledge_base(query))


@function_tool
def get_account_status(ctx: RunContextWrapper[Requester]) -> str:
    """Check the signed-in employee's account: locked or active, failed sign-in attempts,
    whether the security team has put a hold on it, and whether MFA is set up."""
    return as_json(desk.get_account_status(ctx.context.employee_id))


@function_tool
def unlock_account(ctx: RunContextWrapper[Requester]) -> str:
    """Unlock the signed-in employee's locked account.

    The rules are enforced by the system, not by you: it refuses when the security team has put a
    hold on the account, and after 3 unlocks in 24 hours. If it refuses, follow its `what_to_do`.
    """
    return as_json(desk.unlock_account(ctx.context.employee_id))


@function_tool
def send_password_reset_link(ctx: RunContextWrapper[Requester]) -> str:
    """Email a password reset link to the address ON FILE for the signed-in employee.

    You cannot choose the address and you never see the link. Use it when the employee forgot
    their password. Never ask the employee for a password.
    """
    return as_json(desk.send_password_reset_link(ctx.context.employee_id))


@function_tool
def list_software_catalog(ctx: RunContextWrapper[Requester]) -> str:
    """List the software that can be requested, which items are self-service, and how many seats are free."""
    return as_json(desk.list_software_catalog())


@function_tool
def request_software_license(ctx: RunContextWrapper[Requester], software: str) -> str:
    """Assign a software seat to the signed-in employee. Works only for self-service apps with a free seat.

    Args:
        software: The exact name from list_software_catalog, for example "Figma".
    """
    return as_json(desk.request_software_license(ctx.context.employee_id, software))


@function_tool
def create_ticket(ctx: RunContextWrapper[Requester], summary: str, details: str,
                  category: Literal["access", "network", "software", "hardware", "email", "security", "other"]) -> str:
    """Open a ticket for the employee's problem. Do this once per problem, before you act on it.

    Args:
        summary: One line, for example "VPN keeps disconnecting".
        details: What the employee said and what you found so far. A human may read only this.
        category: The area of the problem.
    """
    return as_json(desk.create_ticket(ctx.context.employee_id, summary, details, category))


@function_tool
def get_ticket_status(ctx: RunContextWrapper[Requester], ticket_id: str) -> str:
    """Show the status of one of the employee's tickets, including replies from the service desk team.

    Args:
        ticket_id: For example "IT-1004".
    """
    return as_json(desk.get_ticket_status(ctx.context.employee_id, ticket_id))


@function_tool
def list_my_tickets(ctx: RunContextWrapper[Requester]) -> str:
    """List the signed-in employee's 10 most recent tickets with their status."""
    return as_json(desk.list_tickets(ctx.context.employee_id))


@function_tool
def close_ticket_as_resolved(ctx: RunContextWrapper[Requester], ticket_id: str, resolution: str) -> str:
    """Close a ticket you SOLVED. Only after the fix worked or the knowledge base fully answered the question.

    Args:
        ticket_id: The ticket you opened for this problem.
        resolution: What fixed it, in one or two sentences.
    """
    return as_json(desk.close_ticket(ctx.context.employee_id, ticket_id, resolution))


@function_tool
def escalate_to_human(ctx: RunContextWrapper[Requester], ticket_id: str, reason: str,
                      urgency: Literal["low", "normal", "high", "critical"]) -> str:
    """Hand a ticket to a human service desk colleague, who is alerted by email and Slack.

    Use it when: the knowledge base has no answer, a tool refused and told you to escalate, the
    employee asks for a person, or it is a security incident or a lost device.

    Args:
        ticket_id: The ticket you opened for this problem.
        reason: Why you cannot solve it. A human reads this first, so be specific.
        urgency: critical = security incident or lost device. high = employee cannot work at all.
            normal = default. low = can wait for the next working day.
    """
    return as_json(desk.escalate_ticket(ctx.context.employee_id, ticket_id, reason, urgency))


# ---- the agent ---------------------------------------------------------------------------------
agent = Agent(
    name="KernMart IT service desk",
    instructions=INSTRUCTIONS,
    tools=[
        search_knowledge_base, get_account_status, unlock_account, send_password_reset_link,
        list_software_catalog, request_software_license, create_ticket, get_ticket_status,
        list_my_tickets, close_ticket_as_resolved, escalate_to_human,
    ],
    model=llm.model(),
    model_settings=llm.SETTINGS,
)


async def chat():
    print(llm.start_tracing())
    employee_id = input("Sign in as which employee? (E-1001 Priya, E-1002 Rahul, E-1003 Meera): ").strip()
    memory = SQLiteSession("step01")                      # the conversation, kept in memory for this run
    while True:
        message = input("\nyou > ").strip()
        if not message:
            break
        result = await Runner.run(agent, message, context=Requester(employee_id), session=memory, max_turns=12)
        llm.print_tool_calls(result)
        print(f"\nagent > {result.final_output}")


if __name__ == "__main__":
    asyncio.run(chat())
