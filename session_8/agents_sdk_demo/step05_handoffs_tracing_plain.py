"""
STEP 05 (plain): two agents. Triage reads, a Refund specialist can move money.
Tools, guardrails and approval are imported from step04_approval_plain.py, unchanged, so only the NEW part is here.

Run:  python db.py reset
      python step05_handoffs_tracing_plain.py         (log in as C-100)

Try:  1. Where is my keyboard order KM-49007?          (Triage answers itself: "answered by: Triage")
      2. My headphones KM-50111 arrived 6 days late. I want a refund.
                                                       ("answered by: Refund specialist", and you are asked to approve, as in step 04)

An empty line quits.
"""
import asyncio
from pathlib import Path

from agents import (Agent, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered, Runner, SQLiteSession)

import db
from step04_approval_plain import (Customer, claims_match_ledger, escalate_to_human, get_order, issue_refund,
                                   list_orders, login, model, speed_bump, track_shipment)

# ---- NEW: the specialist
# The only agent that has issue_refund. Its tools are still protected by the rules and the approval from steps 03 and 04.
refund_specialist = Agent[Customer](
    name="Refund specialist",
    handoff_description="Handles refund requests: checks the order and issues refunds.",     # what Triage reads
    instructions=(
        "You handle refund requests for KernMart. The customer is already logged in: never ask for their id. "
        "Always call get_order first to check the order. "
        "Refund policy: only delivered orders, within 30 days of delivery, never more than the order price. "
        "If a refund is refused or a person declines it, tell the customer plainly what happened. "
        "If you cannot resolve something, call escalate_to_human. "
        "Answer the customer in two or three plain sentences."
    ),
    tools=[get_order, issue_refund, escalate_to_human],
    output_guardrails=[claims_match_ledger],
    model=model,
)

# ---- NEW: the front desk
# Triage can read orders but has NO refund tool, so it cannot refund even if it is tricked. That is a missing
# capability, not a rule it might forget.
# handoffs=[...] gives Triage an extra tool, transfer_to_refund_specialist. When the model calls it, the SDK switches
# agents: the next model call runs with the specialist's instructions and tools. It is the same loop with a different worker.
triage = Agent[Customer](
    name="Triage",
    instructions=(
        "You are the KernMart customer-support assistant. The customer is already logged in: never ask for their id. "
        "Answer questions about orders and shipments yourself, using your tools. Never guess order data. "
        "For ANY refund request, hand off to the Refund specialist: you cannot issue refunds. "
        "Answer the customer in two or three plain sentences."
    ),
    tools=[list_orders, get_order, track_shipment],
    handoffs=[refund_specialist],
    input_guardrails=[speed_bump],                         # runs on the FIRST agent only
    output_guardrails=[claims_match_ledger],               # runs on the LAST agent only, so both agents have it
    model=model,
)


def what_happened(result):
    # result.last_agent is the agent that gave the final answer. result.new_items lists everything that happened in the run.
    tools = [getattr(i.raw_item, "name", "?") for i in result.new_items if i.type == "tool_call_item"]
    print(f"   [answered by: {result.last_agent.name} | tool calls: {', '.join(tools) or 'none'}]")


async def chat():
    customer = login()
    session = SQLiteSession(f"step05-{customer.customer_id}", str(Path(__file__).with_name("chat_sessions.db")))
    print(f"Hello {customer.name}. Empty line = quit.")
    while text := input("\nYou > ").strip():
        try:
            # We always start at Triage. If Triage hands off, the SDK switches to the specialist inside this one call.
            result = await Runner.run(triage, text, context=customer, session=session)
            while result.interruptions:
                state = result.to_state()
                for item in result.interruptions:
                    print(f"\n   PAUSED. A person must decide: {item.tool_name}({item.raw_item.arguments})")
                    if input("   You are the approver. Approve? (y/n) > ").strip().lower().startswith("y"):
                        state.approve(item)
                    else:
                        state.reject(item, rejection_message="A person declined this refund.")
                result = await Runner.run(triage, state, context=customer, session=session)
            what_happened(result)                                                           # NEW
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
