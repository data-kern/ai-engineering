"""The MCP server, tested the way an agent uses it: start the real server, connect a real MCP client, call tools.
No model involved. Needs the database:  docker compose up -d postgres mailpit

    pytest tests/test_mcp_server.py
"""
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from servicedesk_core import db

SERVER_FILE = Path(__file__).parent.parent / "mcp_server" / "server.py"


@pytest.fixture(autouse=True)
def fresh_database():
    db.reset()


@asynccontextmanager
async def connected_as(employee_id):
    """A client signed in as one employee, talking to a freshly started server over stdio."""
    environment = {**os.environ, "EMPLOYEE_ID": employee_id} if employee_id else {
        key: value for key, value in os.environ.items() if key != "EMPLOYEE_ID"}
    server = StdioServerParameters(command=sys.executable, args=[str(SERVER_FILE)], env=environment)
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call(session, tool, arguments=None):
    result = await session.call_tool(tool, arguments or {})
    text = result.content[0].text
    return result.isError, (text if result.isError else json.loads(text))


def run(coroutine):
    return asyncio.run(coroutine)


def test_the_server_offers_the_eleven_tools():
    async def scenario():
        async with connected_as("E-1001") as session:
            return {tool.name for tool in (await session.list_tools()).tools}
    names = run(scenario())
    assert len(names) == 11 and {"escalate_to_human", "unlock_account", "search_knowledge_base"} <= names


def test_no_tool_takes_an_employee_id_so_the_model_cannot_choose_whose_account_it_acts_on():
    async def scenario():
        async with connected_as("E-1001") as session:
            return (await session.list_tools()).tools
    for tool in run(scenario()):
        assert "employee_id" not in tool.inputSchema.get("properties", {}), tool.name


def test_urgency_and_category_are_enums_in_the_schema():
    async def scenario():
        async with connected_as("E-1001") as session:
            return {tool.name: tool.inputSchema for tool in (await session.list_tools()).tools}
    schemas = run(scenario())
    assert schemas["escalate_to_human"]["properties"]["urgency"]["enum"] == ["low", "normal", "high", "critical"]
    assert "hardware" in schemas["create_ticket"]["properties"]["category"]["enum"]


def test_each_connection_sees_only_its_own_account():
    async def scenario():
        async with connected_as("E-1002") as rahul:
            rahul_status = await call(rahul, "get_account_status")
        async with connected_as("E-1003") as meera:
            meera_status = await call(meera, "get_account_status")
        return rahul_status, meera_status
    (_, rahul_status), (_, meera_status) = run(scenario())
    assert rahul_status["status"] == "active" and meera_status["security_hold"] is True


def test_a_refusal_is_a_normal_answer_with_instructions_for_the_agent():
    async def scenario():
        async with connected_as("E-1003") as session:
            return await call(session, "unlock_account")
    is_error, answer = run(scenario())
    assert is_error is False and answer["done"] is False and answer["reason"] == "security_hold"


def test_someone_elses_ticket_is_reported_as_an_error():
    async def scenario():
        async with connected_as("E-1001") as priya:
            _, created = await call(priya, "create_ticket",
                                    {"summary": "Printer", "details": "offline", "category": "hardware"})
        async with connected_as("E-1002") as rahul:
            return await call(rahul, "get_ticket_status", {"ticket_id": created["ticket_id"]})
    is_error, message = run(scenario())
    assert is_error is True and "not found" in message


def test_a_connection_without_an_identity_cannot_use_tools():
    async def scenario():
        async with connected_as(None) as session:
            return await call(session, "get_account_status")
    is_error, message = run(scenario())
    assert is_error is True and "Unknown requester" in message


def test_every_call_is_written_to_the_audit_log_with_its_outcome():
    async def scenario():
        async with connected_as("E-1003") as session:
            await call(session, "get_account_status")
            await call(session, "unlock_account")
            await call(session, "get_ticket_status", {"ticket_id": "IT-9999"})
    run(scenario())
    rows = db.query("SELECT employee_id, tool, outcome FROM audit_log ORDER BY id")
    assert [(r["tool"], r["outcome"]) for r in rows] == [
        ("get_account_status", "ok"), ("unlock_account", "refused"), ("get_ticket_status", "error")]
    assert {r["employee_id"] for r in rows} == {"E-1003"}


def test_the_full_escalation_path_through_the_server():
    async def scenario():
        async with connected_as("E-1003") as session:
            _, ticket = await call(session, "create_ticket",
                                   {"summary": "Locked", "details": "security hold", "category": "security"})
            return await call(session, "escalate_to_human",
                              {"ticket_id": ticket["ticket_id"], "reason": "security hold", "urgency": "critical"})
    _, answer = run(scenario())
    assert answer["status"] == "escalated" and answer["expected_response"] == "within 15 minutes"
