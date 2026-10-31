"""
STEP 03 · How does the model use a tool? It ASKS. Nothing runs.

Add:    a tool schema (JSON) sent along with the request, and a real function behind it.
See:    the model does not answer; it replies with `tool_calls`: a name and a JSON string of arguments.
Notice: the function below is NEVER called in this step. The model cannot run code, only ask for it.
Run:    python db.py reset   then   python step03_tool_call.py
Next:   step04_execute.py
"""
import json
import os
import sys

import requests

import db   # plumbing: a real SQLite database with sample orders

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


# 1. The real function: our code, our database. The model cannot see any of this.
def get_order(order_id):
    rows = db.query("SELECT order_id, item, price, status FROM orders WHERE order_id = ?", (order_id,))
    return rows[0] if rows else {"error": "order_not_found"}


# 2. The description of that function: the ONLY thing the model sees.
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
    return r.json()["choices"][0]["message"]


if not API_KEY:
    sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")

messages = [
    {"role": "system", "content": "You are the KernMart customer-support assistant. Use tools to look things up; never guess."},
    {"role": "user", "content": "What is the status of order KM-50111?"},
]

print("TOOLS we send (the model's only view of get_order):")
print(json.dumps(TOOLS, indent=2))

input("\n[ENTER] PREDICT: will the reply be the answer, or something else?")
reply = call_llm(messages)
print("\nRAW REPLY from the model:")
print(json.dumps(reply, indent=2))

call = reply["tool_calls"][0]["function"]
print(f"\nThe model is ASKING for  {call['name']}  with arguments  {call['arguments']!r}")
print("   ^ the arguments are a STRING of JSON, written by the model. It can be wrong or malformed.")
print("\nDid get_order run? NO. We never called it. The model has no way to.")
