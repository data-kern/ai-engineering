"""
STEP 04 (plain): a person approves the big refunds. Same agent as step 03; the changes are marked NEW.

Run:  python db.py reset
      python step04_approval_plain.py                 (log in as C-100)

Try:  1. My phone case KM-50130 arrived cracked. Please refund it.       (EUR 12.99: under the limit, runs alone)
      2. My headphones KM-50111 arrived 6 days late. I want a refund.    (EUR 89: the run PAUSES and asks you.
                                                                          python db.py ledger shows nothing yet.
                                                                          y = refund is made, n = no refund and the agent says why)
      3. Refund me EUR 500 for KM-50111                                  (never reaches you: the rules refuse it first)

/new starts a fresh conversation. An empty line quits.
"""
import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from agents import (Agent, GuardrailFunctionOutput, InputGuardrailTripwireTriggered, OpenAIChatCompletionsModel,
                    OutputGuardrailTripwireTriggered, RunContextWrapper, Runner, SQLiteSession,
                    ToolGuardrailFunctionOutput, function_tool, input_guardrail, output_guardrail,
                    set_tracing_disabled, tool_input_guardrail, tool_output_guardrail)
from openai import AsyncOpenAI

import db

APPROVAL_LIMIT_EUR = 50                       # a demo number: whoever owns the risk sets the real one

set_tracing_disabled(True)
model = OpenAIChatCompletionsModel(
    model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
    openai_client=AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"]),
)


@dataclass
class Customer:
    customer_id: str
    name: str


def login():
    for _ in range(3):
        rows = db.query("SELECT id, name FROM customers WHERE id = ?",
                        (input("Customer id (C-100 or C-200) > ").strip().upper(),))
        if rows:
            return Customer(rows[0]["id"], rows[0]["name"])
        print("   not found, try again")
    raise SystemExit("Could not find that customer id. Goodbye!")


NOT_FOUND = json.dumps({"error": "order_not_found"})


def owned_order(customer_id, order_id):
    rows = db.query("SELECT * FROM orders WHERE order_id = ? AND customer_id = ?", (order_id, customer_id))
    return rows[0] if rows else None


# ================================================================ guardrails: unchanged from step 03
INJECTION = re.compile(r"ignore (all |any |the )?(previous|earlier|above)|disregard (the )?(previous|earlier|above)|"
                       r"you are now|system prompt", re.I)


@input_guardrail
async def speed_bump(ctx, agent, user_input):
    text = user_input if isinstance(user_input, str) else json.dumps(user_input)
    return GuardrailFunctionOutput(output_info=None, tripwire_triggered=bool(INJECTION.search(text)))


def refund_problem(customer_id, order_id, amount):
    """Returns why this refund is not allowed, or None if it is."""
    order = owned_order(customer_id, order_id)
    if not order:
        return {"error": "order_not_found"}
    if order["status"] != "delivered":
        return {"error": "not_delivered_yet"}
    if order["delivered_days_ago"] > 30:
        return {"error": "outside_30_day_window"}
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0 or amount > order["price"]:
        return {"error": "invalid_amount", "max_refund": order["price"]}
    return None


@tool_input_guardrail
def refund_rules(data):
    args = json.loads(data.context.tool_arguments or "{}")
    problem = refund_problem(data.context.context.customer_id, args.get("order_id"), args.get("amount"))
    if problem:
        print(f"   [guardrail] refund refused: {problem}")
        return ToolGuardrailFunctionOutput.reject_content(message=json.dumps(problem))
    return ToolGuardrailFunctionOutput.allow()


INSTRUCTION_LIKE = re.compile(r"issue_refund|refund|please issue|payment|promised|goodwill", re.I)


@tool_output_guardrail
def clean_carrier_notes(data):
    payload = json.loads(data.output)
    if "events" not in payload:
        return ToolGuardrailFunctionOutput.allow()
    removed = 0
    for event in payload["events"]:
        if event.get("note"):
            if INSTRUCTION_LIKE.search(event["note"]):
                event["note"] = "[removed: carrier note looked like an instruction]"
                removed += 1
            else:
                event["note"] = f"(untrusted carrier text) {event['note']}"
    if removed:
        print(f"   [guardrail] removed {removed} carrier note(s) that looked like instructions")
        return ToolGuardrailFunctionOutput.reject_content(message=json.dumps(payload))
    return ToolGuardrailFunctionOutput.allow()


CLAIMS_REFUND = re.compile(r"\b(i|we)('ve| have)\s+(now\s+)?(refunded|issued|processed)|"
                           r"refund (has been|was|is now)\s+(issued|processed|completed|sent)|"
                           r"has been refunded|have been refunded", re.I)


@output_guardrail
async def claims_match_ledger(ctx, agent, output):
    text = output if isinstance(output, str) else str(output)
    in_ledger = any(db.query("SELECT 1 FROM refunds WHERE order_id = ?", (i,)) for i in re.findall(r"KM-\d+", text))
    return GuardrailFunctionOutput(output_info=None,
                                   tripwire_triggered=bool(CLAIMS_REFUND.search(text)) and not in_ledger)


# ================================================================ NEW: when does a person need to look?
# needs_approval= takes a function. The SDK calls it each time the model asks for that tool. If it returns True, the SDK
# does NOT run the tool: the run stops and waits for a person. Here: valid refunds up to EUR 50 run alone, above that a
# person decides. Valid is not the same as looked at.
async def needs_person(ctx, params, call_id):
    """The SDK calls this each time the model asks for issue_refund. True = pause the run for a person."""
    if refund_problem(ctx.context.customer_id, params.get("order_id"), params.get("amount")):
        return False                          # invalid: the rules refuse it anyway, so no human time is spent on it
    return params["amount"] > APPROVAL_LIMIT_EUR


# ================================================================ the tools
@function_tool
def list_orders(ctx: RunContextWrapper[Customer]) -> str:
    """List ALL orders of the logged-in customer (id, item, status)."""
    return json.dumps({"orders": db.query("SELECT order_id, item, status FROM orders WHERE customer_id = ?",
                                          (ctx.context.customer_id,))})


# Groq rejects the schema the SDK writes for a tool the model passes nothing to (it has an empty "required" and no
# additionalProperties). Send the smallest object schema Groq accepts.
list_orders.params_json_schema = {"type": "object", "properties": {}, "additionalProperties": False}


@function_tool
def get_order(ctx: RunContextWrapper[Customer], order_id: str) -> str:
    """Get the details of ONE order: item, price, status, days since delivery. Order ids look like KM-50111."""
    order = owned_order(ctx.context.customer_id, order_id)
    return json.dumps(order) if order else NOT_FOUND


@function_tool(tool_output_guardrails=[clean_carrier_notes])
def track_shipment(ctx: RunContextWrapper[Customer], order_id: str) -> str:
    """Get the shipment tracking events of ONE order."""
    if not owned_order(ctx.context.customer_id, order_id):
        return NOT_FOUND
    return json.dumps({"order_id": order_id, "events": db.query(
        "SELECT event, note FROM shipments WHERE order_id = ? ORDER BY id", (order_id,))})


# Note `int | float`, not `float`: if the model writes 500 and the type were float, the SDK would turn it into 500.0
# and, because the arguments changed, ask a person even for a refund the rules are about to refuse.
@function_tool(needs_approval=needs_person, tool_input_guardrails=[refund_rules])  # NEW: needs_approval
def issue_refund(order_id: str, amount: int | float) -> str:
    """Refund money for ONE order, only after the rules allow it. The amount is in euros and cannot exceed the price."""
    key = f"{order_id}:refund"
    changed = db.run("INSERT INTO refunds(order_id, amount, idem_key) VALUES (?, ?, ?) "
                     "ON CONFLICT(idem_key) DO NOTHING", (order_id, amount, key))
    if changed == 0:
        return json.dumps({"status": "already_refunded", "order_id": order_id})
    return json.dumps({"status": "refunded", "order_id": order_id, "amount": amount})


@function_tool
def escalate_to_human(ctx: RunContextWrapper[Customer], reason: str) -> str:
    """Hand the case to a human colleague when you cannot or should not resolve it."""
    db.run("INSERT INTO escalations(customer_id, reason) VALUES (?, ?)", (ctx.context.customer_id, reason))
    return json.dumps({"status": "escalated"})


agent = Agent[Customer](
    name="KernMart support",
    instructions=(
        "You are the KernMart customer-support assistant. The customer is already logged in: never ask for their id. "
        "Never guess order data: look it up with your tools. "
        "If a lookup fails, recover (for example by listing the customer's orders). "
        "Refund policy: only delivered orders, within 30 days of delivery, never more than the order price. "
        "If a refund is refused or a person declines it, tell the customer plainly what happened. "
        "If you cannot resolve something, call escalate_to_human. "
        "When you have what you need, answer the customer in two or three plain sentences."
    ),
    tools=[list_orders, get_order, track_shipment, issue_refund, escalate_to_human],
    input_guardrails=[speed_bump],
    output_guardrails=[claims_match_ledger],
    model=model,
)


async def chat():
    customer = login()
    session = SQLiteSession(f"step04-{customer.customer_id}", str(Path(__file__).with_name("chat_sessions.db")))
    print(f"Hello {customer.name}. /new = new conversation, empty line = quit.")
    while text := input("\nYou > ").strip():
        if text == "/new":
            await session.clear_session()
            print("(new conversation)")
            continue
        try:
            result = await Runner.run(agent, text, context=customer, session=session)
            # NEW: if a tool needed approval, the run stopped and result.interruptions lists the calls that are waiting.
            while result.interruptions:
                state = result.to_state()          # the paused run as an object. It could be saved as JSON and resumed later
                for item in result.interruptions:
                    print(f"\n   PAUSED. A person must decide: {item.tool_name}({item.raw_item.arguments})")
                    if input("   You are the approver. Approve? (y/n) > ").strip().lower().startswith("y"):
                        state.approve(item)
                    else:
                        state.reject(item, rejection_message="A person declined this refund.")
                # run again from the saved state: the SDK carries on the same run, now with our decisions
                result = await Runner.run(agent, state, context=customer, session=session)
            print(f"\nAgent > {result.final_output}")
        except InputGuardrailTripwireTriggered:
            print("   [guardrail] speed bump: the run was stopped before the agent answered")
            print("\nAgent > I can't act on that request. I've flagged it for a human colleague.")
            db.run("INSERT INTO escalations(customer_id, reason) VALUES (?, ?)", (customer.customer_id, "blocked input"))
        except OutputGuardrailTripwireTriggered:
            print("   [guardrail] the reply claimed a refund the ledger does not show")
            print("\nAgent > I'm not able to confirm that. I've passed your request to a human colleague to check.")
            db.run("INSERT INTO escalations(customer_id, reason) VALUES (?, ?)", (customer.customer_id, "unverified claim"))


if __name__ == "__main__":
    asyncio.run(chat())
