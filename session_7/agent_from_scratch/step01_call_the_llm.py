"""
STEP 01 · An LLM is an HTTP endpoint

Add:    nothing but one POST request. No SDK, no framework.
See:    the exact JSON we send and the exact JSON that comes back.
Notice: the second call has no idea what the first one said. The model is STATELESS.
Run:    export GROQ_API_KEY="gsk_..."   then   python step01_call_the_llm.py
Next:   step02_messages.py
"""
import json
import os
import sys

import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")   # any OpenAI-compatible endpoint
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")                            # must support tool calling later


def call_llm(messages):
    body = {"model": MODEL, "messages": messages, "temperature": 0}
    print("\n--- REQUEST body ---\n" + json.dumps(body, indent=2))
    r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=body, timeout=90)
    if r.status_code != 200:
        sys.exit(f"LLM API said {r.status_code}: {r.text[:300]}")
    data = r.json()
    print("\n--- RESPONSE body ---\n" + json.dumps(data, indent=2))
    return data["choices"][0]["message"]["content"]


if not API_KEY:
    sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")

print("\n=== Call 1 ===")
message1 = call_llm([{"role": "user", "content": "My name is Priya and my order number is KM-50111. Please remember that."}])
print("\n[LLM said]: " + message1)
input("\n[ENTER] Now a SECOND, separate call: does it remember?")
print("\n=== Call 2 ===")
message2 = call_llm([{"role": "user", "content": "What is my order number?"}])
print("\n[LLM said]: " + message2)

