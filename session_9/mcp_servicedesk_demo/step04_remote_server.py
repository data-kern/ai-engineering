"""
STEP 04: the agent talks to an MCP server running as a NETWORK SERVICE. This is the enterprise shape.

The problem in step 03: the server was our child process (stdio), one per user, on one laptop.
The fix: run the server once, as a service. Agents connect to it by URL.

What changed in the agent (two lines):
    step03   MCPServerStdio(params={"command": ..., "args": [...], "env": {...}})
    step04   MCPServerStreamableHttp(params={"url": ..., "headers": {"X-Employee-Id": ...}})

What changed around it:
  - one server serves many agents and many users at once (try two terminals, two employees)
  - it runs where the database is, with ITS credentials; the agent machine holds no database password
  - Kubernetes can probe it (/healthz), and Phoenix can show every tool call it served (set PHOENIX_COLLECTOR_ENDPOINT)
  - you can add a second replica: the server keeps no per-client memory (stateless_http=True)

Run:  docker compose up -d postgres mailpit mcp-server        (or:  python mcp_server/server.py --http  in another terminal)
      python db.py reset
      export GROQ_API_KEY=...
      python step04_remote_server.py
      python step04_remote_server.py --read-only             an agent that may look, but not touch

Try:
  1. As E-1001:  I'm locked out.                   works, exactly like step 03
  2. In a SECOND terminal, as E-1002:  I need Figma.   two employees, one server
  3. Open http://localhost:8030/healthz            {"status":"ok"}: the probe Kubernetes uses
  4. With --read-only, as E-1001:  unlock my account.   the agent never SEES the write tools: least privilege per agent

DEMO LIMIT, said out loud in class: the X-Employee-Id header is not proof. Anyone who can reach port
8030 can claim to be anyone. In production the agent sends a signed token from your identity provider
and the server verifies it (slide 13). Where the id travels is already right: never as a tool argument.

An empty line quits.
"""
import argparse
import asyncio
import os

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStreamableHttp, create_static_tool_filter

import llm
from agent_instructions import INSTRUCTIONS

MCP_URL = os.getenv("MCP_URL", "http://localhost:8030/mcp")

READ_ONLY_TOOLS = ["search_knowledge_base", "get_account_status", "list_software_catalog",
                   "get_ticket_status", "list_my_tickets"]


async def chat(read_only):
    print(llm.start_tracing())
    employee_id = input("Sign in as which employee? (E-1001 Priya, E-1002 Rahul, E-1003 Meera): ").strip()

    server = MCPServerStreamableHttp(
        params={"url": MCP_URL, "headers": {"X-Employee-Id": employee_id}},      # NEW: a URL instead of a command
        cache_tools_list=True,
        client_session_timeout_seconds=30,
        # NEW, optional: this agent may only see the read tools. The server still offers all eleven.
        tool_filter=create_static_tool_filter(allowed_tool_names=READ_ONLY_TOOLS) if read_only else None,
    )

    async with server:
        tools_seen = await server.list_tools()
        print(f"Connected to {MCP_URL}. This agent sees {len(tools_seen)} tools: {', '.join(t.name for t in tools_seen)}")

        agent = Agent(
            name="KernMart IT service desk",
            instructions=INSTRUCTIONS,
            mcp_servers=[server],
            model=llm.model(),
            model_settings=llm.SETTINGS,
        )
        memory = SQLiteSession("step04")
        while True:
            message = input("\nyou > ").strip()
            if not message:
                break
            result = await Runner.run(agent, message, session=memory, max_turns=12)
            llm.print_tool_calls(result)
            print(f"\nagent > {result.final_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-only", action="store_true", help="give the agent only the read tools")
    asyncio.run(chat(parser.parse_args().read_only))
