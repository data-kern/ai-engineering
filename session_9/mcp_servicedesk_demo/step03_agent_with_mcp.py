"""
STEP 03: the SAME agent, with its tools coming from the MCP server. Compare with step01.

What changed (only this):
    step01   tools=[search_knowledge_base, get_account_status, ... eleven @function_tool wrappers ...]
    step03   mcp_servers=[server]            <- the agent asks the server what tools exist

  - The eleven tool functions are GONE from the agent file. Count the lines of the two files.
  - Same instructions, same model, same questions, same behaviour.
  - The employee id no longer travels as `context=`. It travels to the server with the connection
    (here: an environment variable, because stdio starts the server as a child process of this program).

Run:  docker compose up -d postgres mailpit
      python db.py reset
      export GROQ_API_KEY=...
      python step03_agent_with_mcp.py

Try (the same four messages as step01; the answers should match):
  1. As E-1001 (Priya):  I'm locked out of my account.
  2. As E-1001:          How do I connect to the VPN?
  3. As E-1003 (Meera):  I'm locked out of my account.      (security hold: escalate, not unlock)
  4. As E-1002 (Rahul):  I need Figma.
Then:  python db.py audit     one row for EVERY tool call, written by the server, not by the agent.

THE PROBLEM this step leaves:
  stdio means this program started the server as its own child process, on this laptop, with this
  laptop's database password in its environment. One server per user, no sharing, no scaling, nobody
  can watch it, and it dies when this program dies. Step 04 runs the server on the network instead.

An empty line quits.
"""
import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStdio

import llm
from agent_instructions import INSTRUCTIONS

SERVER_FILE = Path(__file__).parent / "mcp_server" / "server.py"


async def chat():
    print(llm.start_tracing())
    employee_id = input("Sign in as which employee? (E-1001 Priya, E-1002 Rahul, E-1003 Meera): ").strip()

    # The child process gets ONLY what the server needs, not our whole environment (which holds the model API key).
    server_env = {"EMPLOYEE_ID": employee_id}
    for name in ("DATABASE_URL", "SMTP_HOST", "SMTP_PORT", "SLACK_WEBHOOK_URL", "PHOENIX_COLLECTOR_ENDPOINT", "PHOENIX_PROJECT_NAME"):
        if name in os.environ:
            server_env[name] = os.environ[name]

    # NEW: describe how to start the server. The SDK starts it, asks it for its tools, and stops it at the end.
    server = MCPServerStdio(
        params={"command": sys.executable, "args": [str(SERVER_FILE)], "env": server_env},
        cache_tools_list=True,                  # ask for the tool list once, not before every model call
        client_session_timeout_seconds=30,
    )

    async with server:                          # NEW: connect (initialize + tools/list happen here)
        agent = Agent(
            name="KernMart IT service desk",
            instructions=INSTRUCTIONS,
            mcp_servers=[server],               # NEW: replaces the eleven function tools
            model=llm.model(),
            model_settings=llm.SETTINGS,
        )
        memory = SQLiteSession("step03")
        while True:
            message = input("\nyou > ").strip()
            if not message:
                break
            result = await Runner.run(agent, message, session=memory, max_turns=12)
            llm.print_tool_calls(result)
            print(f"\nagent > {result.final_output}")


if __name__ == "__main__":
    asyncio.run(chat())
