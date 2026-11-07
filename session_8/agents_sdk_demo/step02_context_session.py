"""
STEP 02 · CONTEXT AND SESSIONS: who is asking is OUR fact, and memory is a table we own

Add:    Two SDK ideas that replace what you hand-built in Session 7.
          context=ChatContext(...)   an object YOUR code passes to Runner.run(). Tools receive it as their first
                                     parameter (`ctx`). It is hidden from the model: it is not in the schema and the
                                     model cannot write to it. This replaces "the model passes the customer id".
          session=SQLiteSession(...) the `messages` list from Session 7's step02, saved to SQLite for you. Each run
                                     loads the earlier turns first and appends the new ones after.
        Login stays our code's job: we ask for the id and check it in the database (production: SSO / one-time code).
Issue:  Step 01 let the model pass the customer id and read ANY order, and every run started from zero.
See:    1. python db.py reset
        2. python step02_context_session.py
           -> scene 1: compare get_order's schema with step 01. There is no customer_id for the model to fill in.
        3. Scene 2 asks, as C-100, for order KM-60001 (C-200's). Step 01 returned it. Now: order_not_found.
        4. Scene 3 asks a follow-up that only makes sense if the agent remembers the last question.
        5. Scene 4 opens sessions.db: the memory is rows in a table. `python step02_context_session.py --chat` to try
           your own questions (log in with C-100 or C-200).
Notice: context is for FACTS (who, which tenant, which permissions): code owns them. A session is for the CONVERSATION
        (what was said). Neither is the run's own state (a half-finished run waiting for approval): that is step 04.
Next:   step03_guardrails.py
"""
import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from agents import Agent, MaxTurnsExceeded, Runner, SQLiteSession, function_tool

import kernmart_tools as kt
import llm
import show

MAX_TURNS = 8
SESSIONS_DB = str(Path(__file__).with_name("sessions.db"))


def build_tools():
    """Every tool takes `ctx` first. The SDK fills it in and hides it from the model."""
    return [function_tool(f) for f in (kt.list_orders, kt.get_order, kt.track_shipment,
                                       kt.check_refund_eligibility, kt.issue_refund, kt.escalate_to_human)]


def build_agent():
    return Agent[kt.ChatContext](name="KernMart support", instructions=kt.INSTRUCTIONS, tools=build_tools(),
                                 model=llm.model(), model_settings=llm.SETTINGS)


def login_flow():
    """OUR code asks who this is and checks the database. Three tries, enforced by a counter, not by a prompt."""
    for _ in range(kt.MAX_LOGIN_TRIES):
        ctx = kt.login(show.ask("Customer id (C-100 or C-200) ➔ "))
        if ctx:
            return ctx
        print("   not found, try again")
    raise SystemExit("Could not find that customer id. Goodbye!")


def turn(agent, ctx, session, text):
    """ONE customer message. context= is OUR facts; session= is the conversation so far."""
    show.customer_says(text)
    try:
        result = Runner.run_sync(agent, text, context=ctx, session=session, hooks=show.Narrator(), max_turns=MAX_TURNS)
    except MaxTurnsExceeded:
        show.blocked("max_turns", f"stopped after {MAX_TURNS} model calls")
        return None
    show.agent_says(result.final_output)
    return result


def chat():
    ctx = login_flow()
    agent, session = build_agent(), SQLiteSession(f"chat-{ctx.customer_id}", SESSIONS_DB)
    show.say(f"Hello {ctx.name}. Empty line to quit. Memory is kept in sessions.db.")
    while (text := show.ask("\n👤 You ➔ ")):
        turn(agent, ctx, session, text)


def scenes():
    show.banner("STEP 02 · Context + Session: identity from code, memory from a table")
    agent = build_agent()

    # ---- scene 1: the schema
    show.say("Scene 1: the same get_order, now with a ctx parameter. What does the MODEL receive?")
    show.predict("Step 01's list_orders needed a customer_id argument. What will list_orders need now?")
    for tool in agent.tools:
        if tool.name in ("get_order", "list_orders"):
            print(f"\n{tool.name}: {json.dumps(tool.params_json_schema['properties'])}")
    show.observe("The customer id is not in the schema",
                 "`ctx` was hidden from the model. list_orders takes NO arguments: whose orders? The ones in\n"
                 "ChatContext, which our login set. The model cannot ask for a different customer.")

    # ---- scene 2: the same attack, now blocked
    ctx = kt.login("C-100")
    session = SQLiteSession("scene-session", SESSIONS_DB)
    asyncio.run(session.clear_session())          # SDK session calls are async
    show.say(f"Scene 2: our code logged in {ctx.name} ({ctx.customer_id}). Same question as step 01's last scene.")
    show.predict("C-100 asks for order KM-60001, which belongs to C-200. What comes back this time?")
    turn(agent, ctx, session, "Show me the details of order KM-60001.")
    show.observe("The tool, not the model, enforces ownership",
                 "order_not_found: 'not yours' and 'does not exist' look the same, so nothing leaks.\n"
                 "The model was never trusted with identity, so there was nothing for it to get wrong.")

    # ---- scene 3: memory
    show.say("Scene 3: memory. Ask about one order, then a follow-up that does not name it.")
    turn(agent, ctx, session, "Where is my keyboard order?")
    show.predict("Next message: 'And how much did it cost?'  Will the agent know what 'it' is?")
    turn(agent, ctx, session, "And how much did it cost?")
    show.observe("The agent remembers because the SESSION replays the earlier turns",
                 "Same as Session 7's step02: the model is stateless, memory is a list we send again.\n"
                 "The SDK stores that list in SQLite and prepends it on every run.")

    # ---- scene 4: look at the table
    show.say("Scene 4: open the file. No magic.")
    with sqlite3.connect(SESSIONS_DB) as conn:
        for row in conn.execute("SELECT id, session_id, substr(message_data, 1, 90) FROM agent_messages "
                                "WHERE session_id = 'scene-session' ORDER BY id LIMIT 6"):
            print("  ", row)
    show.observe("A session is rows in a table you own",
                 "You can query it, expire it, delete it when a customer asks (data protection), or swap SQLite for\n"
                 "a database in production. Clear it and the agent has amnesia: `session.clear_session()`.")
    show.say("Next: step03_guardrails.py. Identity is fixed, but a EUR 500 refund on an EUR 89 order is still possible.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="store_true", help="log in and chat instead of the scripted scenes")
    args = ap.parse_args()
    print(llm.start_tracing())
    chat() if args.chat else scenes()
