"""
STEP 04 · Our code executes the tool and hands the result back

Add:    three things after the model's reply: parse the call, run the real function, append a `tool` message.
        Then call the model a second time.
See:    the model reads the tool result and finally answers in plain language.
Notice: `tool_call_id` links our result to the model's request. The `messages` list is the whole story.
Run:    python db.py reset   then   python step04_execute.py
Next:   step05_loop.py
"""
import json
import os
import sys

import requests

import db

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


def get_order(order_id):
    rows = db.query("SELECT order_id, item, price, status FROM orders WHERE order_id = ?", (order_id,))
    return rows[0] if rows else {"error": "order_not_found"}


REGISTRY = {"get_order": get_order}      # name -> function: the router is just a dict

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_order",
        "description": "Get the details of ONE order: item, price and status. Returns order_not_found if the id is unknown.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order id such as KM-50111"}},
            "required": ["order_id"],
        },
    },
}]


def call_llm(messages):
    body = {"model": MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0}
    r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=body, timeout=90)
    if r.status_code != 200:
        sys.exit(f"LLM API said {r.status_code}: {r.text[:300]}")
    msg = r.json()["choices"][0]["message"]
    # keep only what we must send back (providers add extra fields that the next request may reject)
    clean = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        clean["tool_calls"] = msg["tool_calls"]
    return clean


if not API_KEY:
    sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")

messages = [
    {"role": "system", "content": "You are the KernMart customer-support assistant. Use tools to look things up; never guess."},
    {"role": "user", "content": "What is the status of order KM-50111?"},
]

# ---- 1. The model asks
reply = call_llm(messages)
print("\n1. model REPLIED:", json.dumps(reply, indent=2))
messages.append(reply)

call = reply["tool_calls"][0]
print(f"1. model ASKS raw call:      {call}")

name, raw_args = call["function"]["name"], call["function"]["arguments"]
print(f"1. model ASKS:      {name}({raw_args})")

# ---- 2. Our code runs it
args = json.loads(raw_args) 
print(f"2. our code RECEIVED: {args}")
result = REGISTRY[name](**args)                # look the function up by name and call it
print(f"2. our code RAN it: {result}")

# ---- 3. The result goes back as a `tool` message
messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
print("3. messages we now send back:")
for i, m in enumerate(messages, 1):
    detail = m.get("content") or f"tool_calls -> {m['tool_calls'][0]['function']['name']}"
    extra = f"   [tool_call_id={m['tool_call_id']}]" if m["role"] == "tool" else ""
    print(f"   {i}. {m['role']:<10} {detail[:80]}{extra}")

# ---- 4. The model reads the result and answers
input("\n[ENTER] PREDICT: what will the second reply contain?")
final = call_llm(messages)
print("\n4. second reply:", json.dumps(final, indent=2))
print("\nOne question took TWO model calls and ONE tool run. An agent is this, repeated until the model stops asking.")
