"""
STEP 02 (part 1 of 2): your first MCP server. Two tools, twenty lines.

The problem in step 01: tools were welded into one agent.
The fix: put the tools in a SERVER that any agent or program can connect to.

How to define a tool:
    1. write a normal Python function
    2. put @mcp.tool() on top
    That is all. The server reads three things from your function and sends them to every client:
        the function NAME        -> the tool's name
        the DOCSTRING            -> the description the model reads (this is prompt engineering for tools)
        the TYPE HINTS           -> the JSON schema of the arguments (you never write it by hand)

You do not run this file yourself. A client starts it. Part 2 does that:
    python step02_call_it.py

THE PROBLEM this tiny server leaves (find it in part 2): look at get_account_status.
Who decides WHOSE account is looked up?
"""
from mcp.server.fastmcp import FastMCP

from servicedesk_core import desk

mcp = FastMCP("my-first-server")


@mcp.tool()
def search_knowledge_base(query: str) -> dict:
    """Search the IT knowledge base for how-to articles. Example query: "vpn keeps disconnecting"."""
    return desk.search_knowledge_base(query)


@mcp.tool()
def get_account_status(employee_id: str) -> dict:
    """Check an employee's account: locked or active, failed attempts, security hold."""
    return desk.get_account_status(employee_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")      # stdio: the client starts this file as a child process and talks over stdin/stdout
