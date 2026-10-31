"""
STEP 02 · Memory is a list we re-send

Add:    a `messages` list that grows, and a loop that keeps asking the user for input.
See:    the model "remembers" only because we send the whole conversation every time.
Notice: delete one line from `messages` and it forgets. There is no hidden memory.
Run:    python step02_messages.py        (empty line to quit)
Next:   step03_tool_call.py
"""
import os
import sys

import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


def call_llm(messages):
    body = {"model": MODEL, "messages": messages, "temperature": 0}
    r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=body, timeout=90)
    if r.status_code != 200:
        sys.exit(f"LLM API said {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


if not API_KEY:
    sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")

messages = [{"role": "system", "content": "You are the KernMart customer-support assistant. Be brief."}]

while True:
    user_text = input("\nyou> ").strip()
    if not user_text:
        break
    messages.append({"role": "user", "content": user_text})      # 1. add what the user said
    answer = call_llm(messages)                                   # 2. send EVERYTHING so far
    messages.append({"role": "assistant", "content": answer})    # 3. add what the model said
    print(f"bot> {answer}")
    print(f"     ({len(messages)} messages are re-sent on every call)")
