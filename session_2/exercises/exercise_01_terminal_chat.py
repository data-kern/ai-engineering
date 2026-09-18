import os
import sys
from groq import Groq

"""
╔══════════════════════════════════════════════════════════════╗
║  Exercise 01 — Build a Terminal Chat with Memory            ║
║  Topic: Groq API · Message History · Conversation Loop      ║
╚══════════════════════════════════════════════════════════════╝

Real-world story
────────────────
Every AI chatbot you've ever used — ChatGPT, Claude, Gemini —
is doing one simple thing under the hood:

  1. Collecting the full conversation history into a list
  2. Sending that ENTIRE list to the AI on every message
  3. Appending the AI's reply back to the list

That's it. No magic. Just a growing list of dictionaries.

Your job: wire up those 5 missing steps so this terminal
chatbot can hold a real, multi-turn conversation.

────────────────────────────────────────────────────────────────
What each message dictionary looks like
────────────────────────────────────────────────────────────────
  {"role": "system",    "content": "You are a helpful tutor."}
  {"role": "user",      "content": "What is an LLM?"}
  {"role": "assistant", "content": "An LLM is a large language model..."}

  ✦ "system"    → secret instructions the AI always reads first
  ✦ "user"      → what the human typed
  ✦ "assistant" → what the AI replied

────────────────────────────────────────────────────────────────
Thinking hints  💡
────────────────────────────────────────────────────────────────
  TODO 1 — Start the list with just the system message:
    messages = [ {"role": "system", "content": SYSTEM_PROMPT} ]

  TODO 2 — When user types something, add it to the list:
    messages.append({"role": "user", "content": user_input})

  TODO 3 — Call the Groq API. The key argument is 'messages':
    response = client.chat.completions.create(
        messages=messages,
        model=MODEL
    )

  TODO 4 — Dig the text out of the response object:
    reply = response.choices[0].message.content

  TODO 5 — Save what the AI said so the next turn remembers it:
    messages.append({"role": "assistant", "content": reply})

────────────────────────────────────────────────────────────────
Run it with:   python3 exercise_01_terminal_chat.py
Type 'quit' to exit.
────────────────────────────────────────────────────────────────
"""

# ── API setup — do NOT change ─────────────────────────────────────────────────

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

    # ── TODO 1 ───────────────────────────────────────────────────────────────
    # Create the `messages` list with the system prompt inside it.
    # → Write your code below:


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

        # ── TODO 2 ───────────────────────────────────────────────────────────
        # Add the user's message to the list.
        # → Write your code below:


        # ── TODO 3 ───────────────────────────────────────────────────────────
        # Call the Groq API. Pass the full messages list and MODEL.
        # → Write your code below:


        # ── TODO 4 ───────────────────────────────────────────────────────────
        # Pull the AI's text out of the response.
        # → Replace the placeholder below:
        reply = "..."   # ← change this line

        print(f"\nAI: {reply}\n")

        # ── TODO 5 ───────────────────────────────────────────────────────────
        # Add the AI's reply to the list so the next turn has context.
        # → Write your code below:


if __name__ == "__main__":
    run()
