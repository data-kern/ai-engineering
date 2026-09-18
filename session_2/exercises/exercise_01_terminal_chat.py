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
    print("  EXERCISE 1 — Terminal Chat with Persistent History")
    print("============================================================")
    print("Type your messages below. Type 'quit' or 'exit' to end.\n")

    # TODO 1: Initialize a list called `messages` that contains ONE dictionary.
    # The dictionary should have "role": "system" and "content": SYSTEM_PROMPT.
    # -> Write your code below:
    
    
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

        # TODO 2: Append the user's input to the `messages` list.
        # It needs to be a dictionary with "role": "user".
        # -> Write your code below:
        
        
        # TODO 3: Call the Groq API using client.chat.completions.create().
        # Pass in the FULL `messages` list and the `MODEL`.
        # -> Write your code below:
        
        
        # TODO 4: Extract the AI's text reply from the response object
        # (Hint: response.choices[0].message.content)
        # -> Write your code below:
        reply = "..." # Replace this string with the actual extracted reply
        
        print(f"\nAI: {reply}\n")

        # TODO 5: Append the AI's reply to the `messages` list.
        # It needs to be a dictionary with "role": "assistant".
        # -> Write your code below:
        
        

if __name__ == "__main__":
    run()
