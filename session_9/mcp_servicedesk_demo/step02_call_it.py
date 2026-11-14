"""
STEP 02 (part 2 of 2): talk to an MCP server with a plain client. No LLM, no agent.

This is what every agent framework does under the hood, and what Claude Desktop or an IDE does:
    1. connect and say hello                    (initialize)
    2. ask what tools exist                     (tools/list)   -> names, descriptions, JSON schemas
    3. call one                                 (tools/call)   -> the result

The point: the client knows NOTHING about our tools in advance. It discovers them.

Run:  docker compose up -d postgres mailpit
      python db.py reset
      python step02_call_it.py                                  the tiny server from part 1 (stdio)
      python step02_call_it.py --server full --employee E-1001  the real server (stdio), signed in as Priya
      python step02_call_it.py --url http://localhost:8030/mcp --employee E-1002
                                                                a server running on the network (step 04 starts it)

See:
  1. With the tiny server, the client asks for E-1003's account. The server answers. Nobody checked who
     is asking, because "whose account" is a tool ARGUMENT, and the model (or any client) fills arguments in.
  2. With --server full the tool takes no employee id at all. The server knows who is signed in from the
     connection (the environment variable over stdio, a header over HTTP). There is nothing to fake.
  3. The tool list shows the schema FastMCP generated from the type hints: enum values for urgency, required fields.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

HERE = Path(__file__).parent


def open_connection(args):
    """Return an async context manager that yields (read, write): stdio for a local file, HTTP for a URL."""
    if args.url:
        return streamablehttp_client(args.url, headers={"X-Employee-Id": args.employee})
    if args.server == "full":
        script = HERE / "mcp_server" / "server.py"
    else:
        script = HERE / "step02_first_server.py"
    server = StdioServerParameters(command=sys.executable, args=[str(script)],
                                   env={**os.environ, "EMPLOYEE_ID": args.employee})
    return stdio_client(server)


def show_tools(tools):
    print(f"\nThe server offers {len(tools)} tools:\n")
    for tool in tools:
        arguments = ", ".join(tool.inputSchema.get("properties", {})) or "(none)"
        print(f"  {tool.name:28} arguments: {arguments}")
    print("\nThe full schema of the last tool, exactly as the model will receive it:")
    print(json.dumps(tools[-1].inputSchema, indent=2))


async def call(session, tool_name, arguments):
    print(f"\n>>> {tool_name}({arguments})")
    result = await session.call_tool(tool_name, arguments)
    print(("ERROR: " if result.isError else "") + result.content[0].text[:600])


async def main(args):
    async with open_connection(args) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()                      # 1. hello
            tools = (await session.list_tools()).tools      # 2. what can you do?
            show_tools(tools)

            await call(session, "search_knowledge_base", {"query": "vpn keeps disconnecting"})     # 3. do it

            takes_an_id = "employee_id" in next(t for t in tools if t.name == "get_account_status").inputSchema["properties"]
            if takes_an_id:
                print(f"\nWe are '{args.employee}'. Now ask for ANOTHER employee's account:")
                await call(session, "get_account_status", {"employee_id": "E-1003"})
            else:
                print(f"\nWe are '{args.employee}'. This tool has no employee argument: it can only show our own account.")
                await call(session, "get_account_status", {})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=["tiny", "full"], default="tiny")
    parser.add_argument("--url", help="connect to a server on the network, for example http://localhost:8030/mcp")
    parser.add_argument("--employee", default="E-1001")
    asyncio.run(main(parser.parse_args()))
