"""
STEP 05 · THE AGENT LOOP: think -> act -> observe -> repeat

Add:    a `for` loop around what you wrote in steps 03-04. Call the model; if it asked for tools, run them and
        append the results; if it did not, that is the answer. Five more tools, all real SQL.
        The agent does not know who the customer is: the prompt tells it to ASK for a customer id, in conversation.
Issue:  none yet. This is the BASELINE: it trusts everything the model writes.
See:    1. python db.py reset
        2. python step05_loop.py "Where is my headphones order?"
           -> it asks for your id: answer C-100. No if-statement says "list the orders, then track the shipment":
              the agent picks its own path. One loop = one model call.
        3. python step05_loop.py "I'm C-100. What is the status of order KM-99999?"
           -> a wrong order id: the tool returns an error as DATA and the agent recovers.
           (an id that does not exist, say C-999: the prompt asks the model to give up after three tries. Will it?)
        4. Read `execute()` and `issue_refund()`. Nothing checks what the model asks for.
Notice: this agent TRUSTS everything: the arguments, the customer id the model passes (whatever was typed),
        the amount it refunds. trusted_agent.py is this same loop with that trust taken away, one control at a time.
Next:   trusted_agent.py
"""
import json
import os
import sys
import time

import requests

import db
import show

# ================================================================ configuration
API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = 8                  # stop condition 1: a budget
STEP_NUMBER = "05"

WHO = ("You do not know who the customer is yet. Ask for their customer id (like C-100) and use it in your tool calls. "
       "If it is not found, ask once more; after three failed tries, apologise politely and stop.")
SYSTEM_PROMPT = " ".join([
    "You are the KernMart customer-support assistant.",
    WHO,
    "Never guess order data: look it up with your tools.",
    "Before EVERY tool call, write one short sentence saying what you are about to do and why.",
    "If a lookup fails, recover (for example by listing the customer's orders).",
    "Refund policy: only delivered orders, within 30 days of delivery, never more than the order price.",
    "If you cannot resolve something, call escalate_to_human.",
    "When you have what you need, answer the customer in two or three plain sentences.",
])


# ================================================================ the tools: real functions, real database
def _order(order_id):
    rows = db.query("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    return rows[0] if rows else None


NOT_FOUND = {"error": "order_not_found", "hint": "Call list_orders to see this customer's orders."}


def list_orders(customer_id):
    if not db.query("SELECT 1 FROM customers WHERE id = ?", (customer_id,)):
        return {"error": "customer_not_found", "hint": "Ask the customer to check their customer id."}
    return {"orders": db.query("SELECT order_id, item, status FROM orders WHERE customer_id = ?", (customer_id,))}


def get_order(order_id):
    return _order(order_id) or NOT_FOUND


def track_shipment(order_id):
    if not _order(order_id):
        return NOT_FOUND
    events = db.query("SELECT event, note FROM shipments WHERE order_id = ? ORDER BY id", (order_id,))
    return {"order_id": order_id, "events": events}


def check_refund_eligibility(order_id):
    order = _order(order_id)
    if not order:
        return NOT_FOUND
    if order["status"] != "delivered":
        return {"eligible": False, "reason": "not_delivered_yet"}
    return {"eligible": True, "max_refund": order["price"]}


def issue_refund(order_id, amount):
    """A WRITE tool. Right now it believes whatever the model asks for."""
    db.run("INSERT INTO refunds(order_id, amount) VALUES (?, ?)", (order_id, amount))
    return {"status": "refunded", "order_id": order_id, "amount": amount}


def escalate_to_human(reason, customer_id="unknown"):
    db.run("INSERT INTO escalations(customer_id, reason) VALUES (?, ?)", (customer_id, reason))
    return {"status": "escalated", "note": "A human colleague will contact the customer."}


# ================================================================ what the model sees: JSON schemas
def _fn(name, description, properties=None, required=()):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": list(required)}}}


_ORDER_ID = {"order_id": {"type": "string", "description": "Order id such as KM-50111"}}

TOOLS = [
    _fn("list_orders", "List all orders of a customer (id, item, status). "
        "Use this first when the customer has not given an order id, or the id was not found.",
        {"customer_id": {"type": "string", "description": "Customer id such as C-100"}}, ["customer_id"]),
    _fn("get_order", "Get the details of ONE order: item, price, status, days since delivery. "
        "Returns order_not_found if the id is not the customer's.", _ORDER_ID, ["order_id"]),
    _fn("track_shipment", "Get the shipment tracking events of ONE order.", _ORDER_ID, ["order_id"]),
    _fn("check_refund_eligibility", "Check the refund rules for ONE order. ALWAYS call this before issue_refund.",
        _ORDER_ID, ["order_id"]),
    _fn("issue_refund", "Refund money for ONE order. This changes the customer's money: only call it after "
        "check_refund_eligibility says eligible. The amount cannot exceed the order price.",
        {**_ORDER_ID, "amount": {"type": "number", "description": "Amount in euros"}}, ["order_id", "amount"]),
    _fn("escalate_to_human", "Hand the case to a human colleague when you cannot or should not resolve it.",
        {"reason": {"type": "string", "description": "Why a human is needed"},
         "customer_id": {"type": "string", "description": "The customer's id, if they have given it"}}, ["reason"]),
]


def visible_tools():
    return TOOLS                 # every tool, always. Step 07 makes this depend on who the chat is with


REGISTRY = {   # name -> function: the router is just a dict
    "list_orders": list_orders, "get_order": get_order, "track_shipment": track_shipment,
    "check_refund_eligibility": check_refund_eligibility, "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human,
}


# ================================================================ executing a tool call
def execute(name, raw_arguments):
    """Run the tool the model asked for. (Trusting version: bad input from the model crashes it.)"""
    return REGISTRY[name](**json.loads(raw_arguments or "{}"))


# ================================================================ calling the model
def call_llm(messages):
    """ONE HTTP request. The model is stateless: everything it should know is in `messages`."""
    if not API_KEY:
        sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")
    body = {"model": MODEL, "messages": messages, "tools": visible_tools(), "tool_choice": "auto", "temperature": 0}
    started = time.time()
    r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=body, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"LLM API said {r.status_code}: {r.text[:300]}")
    data = r.json()
    msg = data["choices"][0]["message"]
    assistant = {"role": "assistant", "content": msg.get("content") or ""}      # keep only what we send back
    if msg.get("tool_calls"):
        assistant["tool_calls"] = [{"id": c["id"], "type": "function",
                                    "function": {"name": c["function"]["name"], "arguments": c["function"]["arguments"]}}
                                   for c in msg["tool_calls"]]
    usage = data.get("usage") or {}
    return assistant, {"prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                       "ms": int((time.time() - started) * 1000)}


def new_conversation():
    return [{"role": "system", "content": SYSTEM_PROMPT}]


# ================================================================ THE AGENT
def run_agent(messages, user_text, max_steps=MAX_STEPS):
    """think -> act -> observe -> repeat. A generator: it yields one event per step so we can watch it."""
    messages.append({"role": "user", "content": user_text})

    for step in range(1, max_steps + 1):
        yield {"type": "model_request", "step": step, "messages": list(messages),
               "tool_names": [t["function"]["name"] for t in visible_tools()]}
        assistant, usage = call_llm(messages)                  # THINK: the model reads everything so far
        messages.append(assistant)
        yield {"type": "model_response", "step": step, "message": assistant, "usage": usage}

        calls = assistant.get("tool_calls") or []
        if not calls:                                          # stop condition 2: the model says it is done
            yield {"type": "final", "step": step, "text": assistant["content"]}
            return
        if assistant["content"]:
            yield {"type": "think", "step": step, "text": assistant["content"]}

        for call in calls:                                     # ACT: the model ASKED, our code decides
            name = call["function"]["name"]
            raw_args = call["function"]["arguments"]           # a JSON *string*, exactly as the model wrote it
            yield {"type": "tool_call", "step": step, "id": call["id"], "name": name, "raw_arguments": raw_args}
            result = execute(name, raw_args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})   # OBSERVE
            yield {"type": "observation", "step": step, "id": call["id"], "name": name, "result": result}

    yield {"type": "stopped", "step": max_steps, "reason": f"step limit ({max_steps} loops) reached"}


# ================================================================ a terminal chat around the agent
def main():
    args = sys.argv[1:]
    if "--reset" in args:
        db.reset()
        args.remove("--reset")
    show.banner(f"Agent step {STEP_NUMBER} · model: {MODEL}")
    messages = new_conversation()
    question = " ".join(args) or None
    while True:
        question = question or show.ask("\nyou> ")
        if not question:
            break
        for ev in run_agent(messages, question):
            show.render(ev)
        question = None


if __name__ == "__main__":
    main()
