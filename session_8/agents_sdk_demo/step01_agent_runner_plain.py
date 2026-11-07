"""
STEP 01 (plain): a chat agent with the OpenAI Agents SDK, all in one file.

Run:  python db.py reset
      export GROQ_API_KEY=...            (free key: https://console.groq.com)
      python step01_agent_runner_plain.py

Try:  1. I'm C-100. What orders do I have?
      2. How much was the second one?              (a follow-up: it remembers the conversation)
      3. Show me the details of order KM-60001     (this is C-200's order, and you get it anyway: step 02 fixes that)
      4. Refund me EUR 500 for order KM-50111      (the order cost EUR 89, and it goes through: step 03 fixes that)

/new starts a fresh conversation. An empty line quits.
"""
import asyncio
import json
import os
from pathlib import Path

from agents import Agent, OpenAIChatCompletionsModel, Runner, SQLiteSession, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

import db

# ---- which model: Groq speaks the same API as OpenAI, so the SDK only needs a different client.
# The SDK uploads traces to OpenAI by default. We have no OpenAI key, so switch that off.
set_tracing_disabled(True)
model = OpenAIChatCompletionsModel(
    model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
    openai_client=AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"]),
)


# ---- the tools
# @function_tool turns an ordinary Python function into a tool the model can call.
#   - the docstring is the description the model reads
#   - the type hints (customer_id: str) become the tool's JSON schema, so you never write the schema by hand
@function_tool
def list_orders(customer_id: str) -> str:
    """List ALL orders of a customer (id, item, status). Customer ids look like C-100."""
    return json.dumps({"orders": db.query("SELECT order_id, item, status FROM orders WHERE customer_id = ?",
                                          (customer_id,))})


@function_tool
def get_order(order_id: str) -> str:
    """Get the details of ONE order: item, price, status, days since delivery. Order ids look like KM-50111."""
    rows = db.query("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    return json.dumps(rows[0] if rows else {"error": "order_not_found"})


@function_tool
def track_shipment(order_id: str) -> str:
    """Get the shipment tracking events of ONE order."""
    return json.dumps({"order_id": order_id, "events": db.query(
        "SELECT event, note FROM shipments WHERE order_id = ? ORDER BY id", (order_id,))})


@function_tool
def issue_refund(order_id: str, amount: float) -> str:
    """Refund money for ONE order. The amount is in euros."""
    db.run("INSERT INTO refunds(order_id, amount) VALUES (?, ?)", (order_id, amount))
    return json.dumps({"status": "refunded", "order_id": order_id, "amount": amount})


@function_tool
def escalate_to_human(customer_id: str, reason: str) -> str:
    """Hand the case to a human colleague when you cannot or should not resolve it."""
    db.run("INSERT INTO escalations(customer_id, reason) VALUES (?, ?)", (customer_id, reason))
    return json.dumps({"status": "escalated"})


# ---- the agent
# An Agent is only a description of a worker: a name, instructions, tools and a model. It is not a loop.
agent = Agent(
    name="KernMart support",
    instructions=(
        "You are the KernMart customer-support assistant. "
        "The customer tells you their customer id (like C-100): use it in your tool calls. "
        "Never guess order data: look it up with your tools. "
        "If a lookup fails, recover (for example by listing the customer's orders). "
        "Refund policy: only delivered orders, within 30 days of delivery, never more than the order price. "
        "If you cannot resolve something, call escalate_to_human. "
        "When you have what you need, answer the customer in two or three plain sentences."
    ),
    tools=[list_orders, get_order, track_shipment, issue_refund, escalate_to_human],
    model=model,
)


# ---- the chat
# A session saves every message of the conversation in a SQLite file. On each new message the SDK loads the earlier
# ones and sends them to the model too. That is the only reason "how much was the second one?" works: the model
# itself remembers nothing between calls.
def main():
    session = SQLiteSession("step01", str(Path(__file__).with_name("chat_sessions.db")))
    print("KernMart support. Say who you are, e.g. 'I'm C-100'. /new = new conversation, empty line = quit.")
    while text := input("\nYou > ").strip():
        if text == "/new":
            asyncio.run(session.clear_session())
            print("(new conversation)")
            continue
        # Runner is the loop. This one call asks the model, runs the tools it asks for, sends the results back to
        # the model, and repeats until the model gives a final answer.
        result = Runner.run_sync(agent, text, session=session)
        print(f"\nAgent > {result.final_output}")


if __name__ == "__main__":
    main()
