"""
STEP 05 · HANDOFFS AND TRACES: a router in front, a specialist with the dangerous tool behind it

Add:    handoffs=[...]   one agent can hand the conversation to another. The SDK shows the model a tool named
                         transfer_to_<agent>; calling it makes the NEXT model call run as the other agent: its own
                         instructions, its own tools, its own guardrails.
        Tracing          the SDK records every run as a trace: agent -> model calls -> tools -> handoffs -> input/output guardrails.
                         We send it to Phoenix (llm.start_tracing), the same UI as Session 7. No span code to write:
                         Session 7 needed ~40 lines of hand-made spans.
        Shape: Triage (reads only) -> Refund specialist (eligibility, issue_refund with the rules and the approval).
        This is the "router in front, one agent with a few tools behind it" pattern from the Session 7 architecture slide.
Issue:  Steps 01-04 put every tool, including the one that moves money, on ONE agent. If that agent is fooled, all its
        tools are in reach. And a single agent with a long prompt and many tools gets worse as it grows.
See:    1. In a second terminal:  phoenix serve   (open http://localhost:6006).   python db.py reset
        2. python step05_handoffs_tracing.py
           -> scene 1: a status question. Triage answers alone: NO handoff. Scene 2: a refund request. Triage hands
              off, the specialist checks eligibility and asks for issue_refund, the run PAUSES, you approve here.
        3. Read the tool lists printed under scene 2: Triage has no issue_refund. It cannot call what it does not have.
        4. Open Phoenix, project kernmart-agents-sdk: one trace per run. Find the handoff, the tool spans and the
           input/output guardrail spans. (Tool guardrails show up in the Narrator output, not as their own spans.)
Notice: Guardrails have a SCOPE. Input guardrails run only on the first agent, output guardrails only on the agent that
        ends the run. So the claims check is attached to BOTH agents, and the rules sit on the tool itself, which holds
        wherever the call comes from. Handoffs are not free: each one is another model call and another place to fail.
Next:   the Session 8 slides: evaluation, architectures, and what to build next.
"""
import argparse
import asyncio

from agents import Agent, MaxTurnsExceeded, Runner, SQLiteSession, function_tool, handoff

import db
import kernmart_tools as kt
import llm
import show
from step03_guardrails import claims_match_ledger, fence_carrier_notes, refund_rules_guard, speed_bump
from step04_approval import SESSIONS_DB, needs_person

MAX_TURNS = 10


def build_agents():
    """Two agents. The model is the same; what differs is the instructions and, above all, the TOOLS."""
    refund = Agent[kt.ChatContext](
        name="Refund specialist",
        handoff_description="Handles refund requests: checks eligibility and issues refunds.",
        instructions=kt.INSTRUCTIONS + " You handle refund requests only. Always call check_refund_eligibility first.",
        tools=[function_tool(kt.check_refund_eligibility),
               function_tool(kt.issue_refund, needs_approval=needs_person, tool_input_guardrails=[refund_rules_guard]),
               function_tool(kt.escalate_to_human)],
        output_guardrails=[claims_match_ledger],
        model=llm.model(), model_settings=llm.SETTINGS)
    triage = Agent[kt.ChatContext](
        name="Triage",
        instructions=kt.INSTRUCTIONS + " You answer order-status questions yourself. For ANY refund request, hand off to "
                     "the Refund specialist: you cannot issue refunds.",
        tools=[function_tool(kt.list_orders), function_tool(kt.get_order),
               function_tool(kt.track_shipment, tool_output_guardrails=[fence_carrier_notes])],
        handoffs=[refund],                       # shorthand for handoff(refund)
        input_guardrails=[speed_bump],           # runs on the FIRST agent only
        output_guardrails=[claims_match_ledger],
        model=llm.model(), model_settings=llm.SETTINGS)
    return triage, refund


def describe(item):
    return f"{item.tool_name}({item.raw_item.arguments})"


async def turn(triage, ctx, session, text):
    """One customer message, including any approvals, all in this process (step04 showed the cross-process version)."""
    show.customer_says(text)
    narrator = show.Narrator()                  # one narrator per message, so loop numbers keep counting after a pause
    try:
        result = await Runner.run(triage, text, context=ctx, session=session, hooks=narrator, max_turns=MAX_TURNS)
        while result.interruptions:
            state = result.to_state()
            for item in result.interruptions:
                print(f"\n{show.paint('human', '🙋 PAUSED')}  {describe(item)}")
                if show.ask("approve? (y/n) ➔ ").lower().startswith("y"):
                    state.approve(item)
                else:
                    state.reject(item, rejection_message="A person declined this refund.")
            result = await Runner.run(triage, state, context=ctx, session=session, hooks=narrator, max_turns=MAX_TURNS)
    except MaxTurnsExceeded:
        show.blocked("max_turns", f"stopped after {MAX_TURNS} model calls")
        return None
    show.agent_says(result.final_output)
    return result


async def chat():
    ctx = None
    while ctx is None:
        ctx = kt.login(show.ask("Customer id (C-100 or C-200) ➔ "))
    triage, _ = build_agents()
    session = SQLiteSession(f"chat-{ctx.customer_id}", SESSIONS_DB)
    while (text := show.ask("\n👤 You ➔ ")):
        await turn(triage, ctx, session, text)


async def scenes():
    show.banner("STEP 05 · Handoffs: a router in front, a specialist behind")
    db.reset()
    triage, refund = build_agents()
    ctx = kt.login("C-100")
    session = SQLiteSession("scene-session", SESSIONS_DB)
    await session.clear_session()

    show.say("Scene 1: a status question.")
    show.predict("Does a status question reach the Refund specialist?")
    result = await turn(triage, ctx, session, "Where is my keyboard order KM-49007?")
    if result:
        show.observe("Routing is the model's decision, and it is not always taken",
                     f"last agent: {result.last_agent.name}. Triage had the tools to answer, so there was no handoff.\n"
                     "A router that always hands off is a workflow with extra steps.")

    show.say("Scene 2: a refund request.")
    show.predict("Which agent calls issue_refund? Which agent's tools list contains it?")
    result = await turn(triage, ctx, session, "My headphones KM-50111 arrived 6 days late. I want a refund.")
    print(f"\n{show.paint('bold', 'Triage tools:          ')} {[t.name for t in triage.tools]}")
    print(f"{show.paint('bold', 'Refund specialist tools:')} {[t.name for t in refund.tools]}")
    if result:
        print("\nresult.new_items:")
        for item in result.new_items:
            print("  ", type(item).__name__)
        show.observe("A handoff is a tool call that switches the agent",
                     f"HandoffCallItem -> HandoffOutputItem in the list above; result.last_agent = {result.last_agent.name}.\n"
                     "The loop is the same loop. The next model call just runs with different instructions and tools.")
    show.observe("Least privilege by construction",
                 "Triage cannot refund because issue_refund is not in its tools: not a prompt rule, a missing capability.\n"
                 "If a carrier note fools Triage, the worst it can do is read. The risky tool sits behind the rules\n"
                 "and the approval, on the one agent that needs it.")

    show.observe("One trace per run, free",
                 "Open Phoenix (http://localhost:6006), project kernmart-agents-sdk: Triage -> handoff -> Refund specialist,\n"
                 "each model call with its tokens, each tool call with its arguments, each input/output guardrail with its verdict.\n"
                 "Not running? `phoenix serve` in another terminal and run this step again.")
    show.say("That is the whole SDK tour. In the slides: how to know it WORKS (evals), and which architecture to pick.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="store_true", help="log in and chat instead of the scripted scenes")
    args = ap.parse_args()
    print(llm.start_tracing())
    asyncio.run(chat() if args.chat else scenes())
