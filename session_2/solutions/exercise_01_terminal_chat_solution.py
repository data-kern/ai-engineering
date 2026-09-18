import os
import sys
from groq import Groq

# ── Guard: API key ──────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found. Run: export GROQ_API_KEY='your_key'\n")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "You are a friendly AI Engineering tutor at DataKern."

def run():
    print("\n============================================================")
    print("  EXERCISE 1 SOLUTION — Terminal Chat with Persistent History")
    print("============================================================")
    print("Type your messages below. Type 'quit' or 'exit' to end.\n")

    # SOLUTION 1: Initialize list
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("\n👋 Goodbye!")
            break

        # SOLUTION 2: Append user input
        messages.append({"role": "user", "content": user_input})
        
        # SOLUTION 3: Call API
        response = client.chat.completions.create(
            messages=messages,
            model=MODEL
        )
        
        # SOLUTION 4: Extract reply
        reply = response.choices[0].message.content
        print(f"\nAI: {reply}\n")

        # SOLUTION 5: Append assistant reply
        messages.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    run()
