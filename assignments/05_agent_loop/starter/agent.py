#!/usr/bin/env python3
"""
KernMart Support Agent: ASSIGNMENT STARTER
==========================================
A read-only customer-support agent in plain Python: a loop, tools, stop conditions.
Your job: fill in every  TODO  (search for "TODO"). Everything else is given.

    python check_my_work.py            offline self-check (no API key needed)
    python agent.py A                  run a ready-made scenario (A-G) with a real model
    python agent.py "Where is KM-50111?" --customer C-1003
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from setup_db import connect, reset_db

TODAY = date(2026, 10, 20)          # frozen, so every run sees the same world
MAX_STEPS = 6                       # stop condition 1: number of model calls
TOKEN_BUDGET = 20_000               # stop condition 2: tokens over all steps together
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
STOP_REPLY = "I need a colleague to look at this properly, so I've passed your case on. They will follow up by email."


# ═══════════════════════════════════════════════════════════════════════════
# PART 0: CONSOLE HELPERS (GIVEN)
# ═══════════════════════════════════════════════════════════════════════════
def paint(text: str, colour: int) -> str:
    return text if os.getenv("NO_COLOR") else f"\033[38;5;{colour}m{text}\033[0m"


def short(obj, n: int = 200) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"


def show_model_turn(step: int, reply: dict) -> None:
    print(paint(f"\n── step {step} · the MODEL decides ─────────────────────", 208))
    if reply["content"]:
        print(paint(f"🧠 says: {short(reply['content'])}", 208))
    for tc in reply["tool_calls"]:
        args = {k: v for k, v in tc["args"].items() if k != "why"}
        print(paint(f"🧠 wants to call → {tc['name']}({', '.join(f'{k}={v!r}' for k, v in args.items())})", 208))
        if tc["args"].get("why"):
            print(paint(f"   why: “{tc['args']['why']}”", 208))


def show_tool_result(name: str, result: str) -> None:
    print(paint(f"⚙️  CODE ran {name} → {short(result)}", 43))


def show_stop(reason: str) -> None:
    print(paint(f"🛑 CODE stop condition hit: {reason}", 203))


def show_final(result: dict) -> None:
    print(paint("\n💬 Reply to the customer:", 78))
    print("   " + result["reply"].replace("\n", "\n   "))
    print(paint(f"   status={result['status']} · steps={result['steps']} · tokens={result['tokens']}", 245))


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: THE MODEL (GIVEN). One function. Everything else talks to call_llm() only.
# ═══════════════════════════════════════════════════════════════════════════
def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Send the conversation (+ tool specs) to the model. Returns {"content", "tool_calls", "tokens"}."""
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Missing package. Run: pip install -r requirements.txt")
    if not os.getenv("GROQ_API_KEY"):
        sys.exit('GROQ_API_KEY is not set. Free key: https://console.groq.com  then:  export GROQ_API_KEY="gsk_..."')

    wire = []                                    # our neutral format → the OpenAI/Groq wire format
    for m in messages:
        if m["role"] == "assistant":
            d = {"role": "assistant", "content": m.get("content") or None}
            if m.get("tool_calls"):
                d["tool_calls"] = [{"id": t["id"], "type": "function",
                                    "function": {"name": t["name"], "arguments": json.dumps(t["args"])}}
                                   for t in m["tool_calls"]]
            wire.append(d)
        elif m["role"] == "tool":
            wire.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        else:
            wire.append({"role": m["role"], "content": m["content"]})
    kwargs = {}
    if tools:
        kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"])
    r = client.chat.completions.create(model=MODEL, messages=wire, **kwargs)
    msg = r.choices[0].message
    return {"content": msg.content or "",
            "tool_calls": [{"id": c.id, "name": c.function.name, "args": json.loads(c.function.arguments or "{}")}
                           for c in (msg.tool_calls or [])],
            "tokens": r.usage.total_tokens}


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: TOOLS. Plain Python functions the model may ASK for. It never runs them.
# ═══════════════════════════════════════════════════════════════════════════
# Design rule: WHO the customer is comes from the login session (ctx), never from the model.
# Every tool receives ctx as its first argument and enforces ownership itself.
def own_order(ctx: dict, order_id: str):
    """Fetch an order only if it belongs to the customer in ctx. Returns (row, None) or (None, error_dict)."""
    con = connect()
    row = con.execute("SELECT * FROM orders WHERE id=?", (str(order_id).strip().upper(),)).fetchone()
    con.close()
    if row is None or row["customer_id"] != ctx["customer_id"]:      # same answer for both → we leak nothing
        return None, {"error": "order_not_found", "hint": "Check the order id or use list_orders."}
    return row, None


def get_customer(ctx):
    con = connect()
    r = con.execute("SELECT name, email, tier FROM customers WHERE id=?", (ctx["customer_id"],)).fetchone()
    con.close()
    return dict(r)


def list_orders(ctx):
    con = connect()
    rows = con.execute("SELECT id, item, total_cents, status, promised_on, delivered_on FROM orders "
                       "WHERE customer_id=? ORDER BY ordered_on DESC", (ctx["customer_id"],)).fetchall()
    con.close()
    return {"orders": [{"order_id": r["id"], "item": r["item"], "total_eur": r["total_cents"] / 100,
                        "status": r["status"], "promised_on": r["promised_on"], "delivered_on": r["delivered_on"]}
                       for r in rows]}


def get_order(ctx, order_id):
    """WORKED EXAMPLE. Read it slowly: it is the pattern for your own tools."""
    order, err = own_order(ctx, order_id)
    if err:
        return err
    return {"order_id": order["id"], "item": order["item"], "total_eur": order["total_cents"] / 100,
            "status": order["status"], "ordered_on": order["ordered_on"], "promised_on": order["promised_on"],
            "delivered_on": order["delivered_on"], "payment_method": order["payment_method"]}


POLICY = {
    "late delivery": "Orders delivered more than 3 days after the promised date qualify for a refund or a replacement.",
    "damaged faulty broken": "Damaged or faulty items can be reported within 14 days of delivery for a refund or a replacement.",
    "not received missing delivered": "If tracking says delivered but the parcel is missing: escalate to a human for a carrier investigation. No refund before the investigation result.",
    "return change of mind": "Change of mind: return within 30 days of delivery, item unused. Refund after the return is received.",
    "refund method payment": "Refunds always go back to the original payment method, never to another account.",
}


def search_policy(ctx, topic):
    words = set(str(topic).lower().replace("?", " ").replace(",", " ").split())
    hits = [text for keys, text in POLICY.items() if words & set(keys.split())]
    return {"policy": hits or ["No matching policy. Escalate to a human."]}


def track_shipment(ctx, order_id):
    """TODO 1: return the carrier tracking events of ONE order.

    Follow the pattern of get_order() above:
      1. fetch the order with own_order(): if it returns an error, return that error (ownership!)
      2. query the shipment_events table for this order, oldest event first
         (columns: order_id, ts, text; the `id` column keeps insertion order)
      3. return {"carrier": ..., "tracking_no": ..., "events": [{"date": ..., "event": ...}, ...]}
    Remember to close the connection.
    """
    raise NotImplementedError("TODO 1")


def check_refund_eligibility(ctx, order_id, reason):
    """TODO 2: KernMart's refund rules, in CODE (not in the prompt).

    Return {"eligible": bool, "rule": str, "explanation": str, "max_refund_eur": float}.
    max_refund_eur is the order total in EUROS if eligible, else 0.

        reason            eligible when
        ----------------  --------------------------------------------------
        late_delivery     delivered MORE than 3 days after promised_on
        damaged_item      delivered 14 days ago or less (use TODAY)
        change_of_mind    delivered 30 days ago or less (use TODAY)
        not_received      NEVER automatic: a human must investigate
        anything else     not eligible (rule "unknown_reason")

    Also: an order with no delivered_on is not eligible (rule "not_delivered").
    The explanation is read by the MODEL, so make it concrete ("Delivered 6 day(s) after ...").
    Hint: date.fromisoformat("2026-10-16") gives a date; subtracting two dates gives a timedelta (.days).
    """
    order, err = own_order(ctx, order_id)
    if err:
        return err
    raise NotImplementedError("TODO 2")


# The MODEL never sees the code above. It sees only name + description + argument schema (below).
# The description is effectively a prompt: it decides WHEN the model picks the tool.
WHY = {"type": "string", "description": "One short sentence: why you are calling this tool now."}


def spec(name: str, description: str, props: dict | None = None, required: tuple = ()) -> dict:
    """Build a tool spec. Every tool gets a mandatory `why` argument so the trace explains itself."""
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": {**(props or {}), "why": WHY},
                           "required": [*required, "why"]}}


ORDER_ID = {"type": "string", "description": "Order id like KM-48213"}

# TODO 3: finish the two specs below. The DESCRIPTION is a prompt: it decides WHEN the model picks the tool.
# Say what the tool returns, when to use it, and (for eligibility) when it MUST be used.
# Look at the given specs in TOOL_SPECS to see how spec(name, description, props, required) is called.
TRACK_SHIPMENT_SPEC = spec(
    "track_shipment",
    "",                      # ← TODO 3a: description
    {},                      # ← TODO 3a: properties (hint: ORDER_ID is already defined above)
    (),                      # ← TODO 3a: which properties are required?
)

CHECK_ELIGIBILITY_SPEC = spec(
    "check_refund_eligibility",
    "",                      # ← TODO 3b: description
    {},                      # ← TODO 3b: order_id, plus `reason`. Restrict `reason` to the 4 allowed values
    (),                      # ← TODO 3b
)

TOOL_SPECS = [
    spec("get_customer", "Get the profile of the customer you are talking to (name, email, tier)."),
    spec("list_orders", "List all orders of this customer (id, item, price, status, dates). Use it when no order id is known."),
    spec("get_order", "Get the details of ONE order of this customer.", {"order_id": ORDER_ID}, ("order_id",)),
    spec("search_policy", "Look up KernMart's written support policy for a topic (e.g. 'late delivery', 'damaged', 'return').",
         {"topic": {"type": "string", "description": "Short topic, e.g. 'damaged item'"}}, ("topic",)),
    TRACK_SHIPMENT_SPEC,
    CHECK_ELIGIBILITY_SPEC,
]

TOOL_FUNCS = {
    "get_customer": get_customer, "list_orders": list_orders, "get_order": get_order,
    "search_policy": search_policy, "track_shipment": track_shipment,
    "check_refund_eligibility": check_refund_eligibility,
}


def execute_tool(name: str, args: dict, ctx: dict) -> str:
    """TODO 4: the gap between "the model asked" and "our code ran it".

    Must ALWAYS return a JSON string (json.dumps) and NEVER raise: errors are data the model can read.
      1. `why` is a rationale for humans, not an argument of the Python function: remove it from args
      2. unknown tool name        → {"error": "unknown_tool", "detail": ...}
      3. wrong/missing arguments  → {"error": "bad_arguments", "detail": ...}   (Python raises TypeError)
      4. any other exception      → {"error": "tool_failed", "detail": ...}     (a broken tool must not crash the agent)
      5. otherwise                → run  TOOL_FUNCS[name](ctx, **args)
    Finish with show_tool_result(name, result) so you can watch it, then return the result.
    """
    raise NotImplementedError("TODO 4")


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: THE AGENT LOOP
# ═══════════════════════════════════════════════════════════════════════════
RULES = """Rules:
- Work step by step and call exactly ONE tool at a time. Every tool call needs a short "why".
- Use only facts from tool results. Never guess order details, dates or amounts.
- If a tool returns an error, adapt (for example use list_orders when an order id is not found). Never repeat the same failing call.
- You can only READ information. You cannot issue refunds: tell the customer what you found and what a human colleague would do next.
- When you are done, reply to the customer in 2-4 friendly, plain sentences (without calling a tool)."""


def build_system_prompt(customer_id: str) -> str:
    con = connect()
    c = con.execute("SELECT name, tier FROM customers WHERE id=?", (customer_id,)).fetchone()
    con.close()
    return (f"You are KernMart's customer support agent (KernMart is an online retailer in the Netherlands). "
            f"Today is {TODAY}. You are talking to {c['name']} (customer {customer_id}, {c['tier']} tier).\n\n{RULES}")


def finish(status: str, reply: str, step: int, tokens: int) -> dict:
    result = {"reply": reply, "status": status, "steps": step, "tokens": tokens}
    show_final(result)
    return result


def run_agent(customer_id: str, user_message: str, llm=call_llm) -> dict:
    """TODO 5: one customer request, start to finish.

    think → act → observe → repeat, until the model answers in plain text or a stop condition fires.
    `llm` is injectable so check_my_work.py can test your loop without any API key.
    """
    ctx = {"customer_id": customer_id}                 # identity comes from the session, NEVER from the model
    messages = [{"role": "system", "content": build_system_prompt(customer_id)},
                {"role": "user", "content": user_message}]
    step, tokens = 0, 0

    while True:
        raise NotImplementedError("TODO 5: delete this line, then write 5a-5e below")

        # 5a. STOP CHECK. Code decides, every lap, BEFORE paying for another model call.
        #     If step >= MAX_STEPS or tokens >= TOKEN_BUDGET:  show_stop(reason) and
        #     return finish(status, STOP_REPLY, step, tokens).  Use a different status for each
        #     reason, e.g. "stopped:max_steps" and "stopped:token_budget".

        # 5b. THINK. Ask the model what to do next:  reply = llm(messages, tools=TOOL_SPECS)
        #     Count the step (one per model call) and add reply["tokens"] to the running total.
        #     Then call show_model_turn(step, reply) to watch the decision.

        # 5c. REMEMBER. The model is stateless: it only knows what you send. Append the model's turn to
        #     `messages` as {"role": "assistant", "content": ..., "tool_calls": ...} using the reply.

        # 5d. DONE? If the model requested no tool, it has answered:  return finish("done", <its text>, step, tokens)

        # 5e. ACT + OBSERVE. For every tool call the model requested (there can be several in one turn):
        #     run it with execute_tool(name, args, ctx) and append the result to `messages` as
        #     {"role": "tool", "tool_call_id": <the request's id>, "name": <tool name>, "content": <result string>}
        #     Then the loop goes round again and the model sees what happened.


# ═══════════════════════════════════════════════════════════════════════════
# PART 4: SCENARIOS (GIVEN)
# ═══════════════════════════════════════════════════════════════════════════
SCENARIOS = {
    "A": ("C-1003", "Hi! Where is my desk lamp? Order KM-50111."),
    "B": ("C-1001", "Hi, my headphones (order KM-48213) arrived 6 days late. I want my money back please."),
    "C": ("C-1003", "Hello, I'm still waiting for order KM-48231. Where is it?"),
    "D": ("C-1001", "The USB-C cable from order KM-48100 arrived damaged. Can I get a refund?"),
    "E": ("C-1003", "Where is my order KM-48213? It has my headphones in it."),
    "F": ("C-1003", "My desk lamp KM-50111 is late and I want a refund right now."),
    "G": ("C-1001", "What's the weather like in Amsterdam today?"),
}


def main() -> None:
    p = argparse.ArgumentParser(description="KernMart support agent")
    p.add_argument("request", help="a scenario letter (A-G) or free text")
    p.add_argument("--customer", default="C-1001", help="customer id for free-text requests (C-1001, C-1002, C-1003)")
    a = p.parse_args()
    customer, text = SCENARIOS.get(a.request.upper(), (a.customer, a.request))
    reset_db()
    print(paint(f"Customer {customer} says: “{text}”", 245))
    run_agent(customer, text)


if __name__ == "__main__":
    main()
