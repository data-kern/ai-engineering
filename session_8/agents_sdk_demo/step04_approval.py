"""
STEP 04 · HUMAN APPROVAL: pause the run, save it, resume it in another process

Add:    needs_approval=  on a tool. When the model asks for that tool and the answer is "yes, a person must look",
                         the SDK does NOT run it. The run STOPS and hands you `result.interruptions`: the pending
                         tool calls. You decide per call: state.approve(item) or state.reject(item, rejection_message=...).
        RunState         the paused run as an object. `state.to_string()` is JSON you can store anywhere;
                         `RunState.from_string(agent, text)` brings it back, in a new process, hours later.
        This is Session 6's `runs` table and Session 7's `approval` control, built into the SDK. Our tier is the same:
        a refund up to EUR 50 runs alone, above it a person decides.
Issue:  Step 03's rules say a EUR 89 refund on an EUR 89 order is VALID. Valid is not the same as looked at: nobody
        decided that EUR 89 should leave the company.
See:    1. python db.py reset
        2. python step04_approval.py
           -> scene 1: a EUR 12.99 refund runs by itself (low tier). Scene 2: a EUR 89 refund PAUSES. Then
              `python db.py ledger`: the money has not moved. The run is saved to pending_run.json. Press ENTER and
              this process exits, like a crash, a deploy, or the approver going home.
        3. python step04_approval.py --resume          (a NEW process)
           -> it reads pending_run.json, shows what is waiting, asks YOU: approve (a) or reject with feedback (r).
              Approve: one ledger row. Run the scene again after `python db.py reset`, choose reject: no row, and the
              model tells the customer why.
        4. Note `needs_person` below: a EUR 500 request on an EUR 89 order never reaches a human. The rules refuse it first.
Notice: The SDK stops the run and gives you the state; WHO is asked, how, and for how long is your system (a queue,
        Slack, a ticket). Editing the amount has no button: reject with a message ("refund EUR 50 instead") and let the
        model ask again. The idempotency key from step 03 still makes a double-approve harmless.
Next:   step05_handoffs_tracing.py
"""
import argparse
import asyncio
import json
from pathlib import Path

from agents import (Agent, MaxTurnsExceeded, Runner, RunState, SQLiteSession, function_tool)

import db
import kernmart_tools as kt
import llm
import show
from step03_guardrails import (claims_match_ledger, fence_carrier_notes, refund_rules_guard, speed_bump)

MAX_TURNS = 8
HERE = Path(__file__).parent
SESSIONS_DB = str(HERE / "sessions.db")
PENDING = HERE / "pending_run.json"           # in production: a database row, a queue message


# ================================================================ the new part: WHEN does a person need to look?
async def needs_person(ctx, params, call_id):
    """Called by the SDK each time the model asks for issue_refund. True = pause for a person."""
    problem = kt.refund_rules(ctx.context.customer_id, params.get("order_id"), params.get("amount"))
    if problem:
        return False        # invalid: the rules guardrail refuses it, so no human time is spent on it
    return params["amount"] > kt.APPROVAL_LIMIT_EUR


def build_agent():
    tools = [function_tool(f) for f in (kt.list_orders, kt.get_order, kt.check_refund_eligibility, kt.escalate_to_human)]
    tools += [function_tool(kt.track_shipment, tool_output_guardrails=[fence_carrier_notes]),
              function_tool(kt.issue_refund, needs_approval=needs_person, tool_input_guardrails=[refund_rules_guard])]
    return Agent[kt.ChatContext](name="KernMart support", instructions=kt.INSTRUCTIONS, tools=tools,
                                 input_guardrails=[speed_bump], output_guardrails=[claims_match_ledger],
                                 model=llm.model(), model_settings=llm.SETTINGS)


def describe(item):
    return f"{item.tool_name}({item.raw_item.arguments})"


async def run(agent, source, ctx, session):
    """One run. Returns the result; if the run paused, result.interruptions is not empty."""
    try:
        return await Runner.run(agent, source, context=ctx, session=session, hooks=show.Narrator(), max_turns=MAX_TURNS)
    except MaxTurnsExceeded:
        show.blocked("max_turns", f"stopped after {MAX_TURNS} model calls")


def save(result, ctx, session_id):
    PENDING.write_text(json.dumps({"customer_id": ctx.customer_id, "session_id": session_id,
                                   "state": result.to_state().to_string()}))


async def scenes():
    show.banner("STEP 04 · Approval: the run pauses, the state is saved, a person decides")
    db.reset()
    PENDING.unlink(missing_ok=True)
    agent, ctx = build_agent(), kt.login("C-100")
    session = SQLiteSession("scene-session", SESSIONS_DB)
    await session.clear_session()

    show.say("Scene 1: a small refund. Phone case KM-50130, EUR 12.99, delivered 3 days ago, customer says it is cracked.")
    show.predict("EUR 12.99 is under our EUR 50 limit. Does the run pause?")
    customer = "My phone case KM-50130 arrived cracked. Please refund it."
    show.customer_says(customer)
    result = await run(agent, customer, ctx, session)
    show.agent_says(result.final_output if result and not result.interruptions else "(paused)")
    show.observe("Autonomy is earned per action",
                 "Low value, valid, logged in the ledger: it ran alone. Same agent, same tool, a different answer\n"
                 "from needs_person. The risk lives in the ACTION, not in the agent.")

    show.say("Scene 2: the late headphones, KM-50111, EUR 89. Valid under the rules. Over the limit.")
    show.predict("The model will ask for issue_refund(KM-50111, 89). Does our function run?")
    customer = "My headphones KM-50111 arrived 6 days late. I want a refund."
    show.customer_says(customer)
    result = await run(agent, customer, ctx, session)
    if not result or not result.interruptions:
        show.say("The agent did not reach issue_refund this time (a real model varies). Run it again after db.py reset.")
        return
    for item in result.interruptions:
        print(f"\n{show.paint('human', '🙋 PAUSED')}  waiting for a person: {describe(item)}")
    db.print_table("refunds")
    show.observe("The run STOPPED before the tool ran",
                 "result.interruptions lists the pending calls. The ledger shows only the EUR 12.99 phone case:\n"
                 "the EUR 89 refund has not happened. The model does not know it is waiting; nothing is 'sleeping'.")

    save(result, ctx, "scene-session")
    print(f"\n💾 saved {PENDING.name}: {PENDING.stat().st_size} bytes")
    print(PENDING.read_text()[:400] + " …")
    show.observe("The paused run is just JSON",
                 "RunState holds the conversation so far and the pending call. Store it in a table or a queue and the\n"
                 "approver can answer in an hour. It replaces the `runs` table from Session 6.")
    show.say("Press ENTER and this process exits, like a crash. Then run:  python step04_approval.py --resume")
    show.pause()


async def resume():
    show.banner("STEP 04 · RESUME: a new process, the same run")
    if not PENDING.exists():
        raise SystemExit("Nothing to resume. Run `python step04_approval.py` first.")
    saved = json.loads(PENDING.read_text())
    ctx = kt.login(saved["customer_id"])
    agent = build_agent()
    session = SQLiteSession(saved["session_id"], SESSIONS_DB)
    state = await RunState.from_string(agent, saved["state"], context_override=ctx)

    for item in state.get_interruptions():
        print(f"\n{show.paint('human', '🙋 WAITING')}  {describe(item)}")
        show.predict("You are the approver. Approve this refund, or reject it with feedback?")
        answer = show.ask("approve (a) or reject (r) ➔ ").lower()
        if answer.startswith("a"):
            state.approve(item)
        else:
            why = show.ask("feedback for the agent ➔ ") or "A person declined this refund."
            state.reject(item, rejection_message=why)

    result = await run(agent, state, ctx, session)
    if result:
        show.agent_says(result.final_output)
    PENDING.unlink(missing_ok=True)
    db.print_table("refunds")
    show.observe("The decision, not the model, controls the money",
                 "Approved: the SDK now runs issue_refund and the ledger has one new row.\n"
                 "Rejected: the tool never ran; your feedback went to the model as the tool's result, and it told the\n"
                 "customer. Either way, the SAME run continued where it stopped.")


async def chat():
    ctx = None
    while ctx is None:
        ctx = kt.login(show.ask("Customer id (C-100 or C-200) ➔ "))
    agent, session = build_agent(), SQLiteSession(f"chat-{ctx.customer_id}", SESSIONS_DB)
    while (text := show.ask("\n👤 You ➔ ")):
        result = await run(agent, text, ctx, session)
        while result and result.interruptions:                       # approve here, in the same process
            state = result.to_state()
            for item in result.interruptions:
                print(f"\n{show.paint('human', '🙋 PAUSED')}  {describe(item)}")
                if show.ask("approve? (y/n) ➔ ").lower().startswith("y"):
                    state.approve(item)
                else:
                    state.reject(item, rejection_message="A person declined this refund.")
            result = await run(agent, state, ctx, session)
        if result:
            show.agent_says(result.final_output)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="a NEW process: load pending_run.json and decide")
    ap.add_argument("--chat", action="store_true", help="free chat; approvals are asked in the same process")
    args = ap.parse_args()
    print(llm.start_tracing())
    asyncio.run(resume() if args.resume else chat() if args.chat else scenes())
