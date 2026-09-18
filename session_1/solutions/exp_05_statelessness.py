"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 4: Statelessness — The Model Has No Memory
=======================================================================

WHAT THIS DEMONSTRATES:
  The raw LLM API is COMPLETELY STATELESS. Each API call is independent.
  The model has zero memory of any previous calls — even ones made
  1 second earlier.

  ChatGPT FEELS like it remembers because the ChatGPT *product* appends
  the full conversation history to every request behind the scenes.
  We must do the same thing in our own applications.

THE ANALOGY:
  Imagine a consultant who is brilliant but has amnesia.
  Every time you call them, you must re-explain your entire situation
  from the beginning. They have no notes. Every call is the first call.

INSTRUCTOR NOTES:
  → This is a CRITICAL concept. Most beginners assume the API is stateful.
  → Run Part A first (two calls WITHOUT history) → model forgets.
  → Then run Part B (two calls WITH history passed) → model remembers.
  → The visual diff is shocking and memorable.
  → Bridge to: "What happens to costs as history grows? What about the context window limit?"

SETUP:
  pip install groq
  export GROQ_API_KEY="your_key_from_console.groq.com"
=======================================================================
"""

import os
import sys
from groq import Groq

if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found. Run: export GROQ_API_KEY='your_key'\n")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


# -----------------------------------------------------------------------
# PROMPTS
# -----------------------------------------------------------------------

SYSTEM_PROMPT = "You are a friendly and helpful assistant."

# Turn 1: Introduce personal information
USER_TURN_1 = "My name is Aisha. I am learning AI Engineering at DataKern and I want to become an AI Engineer."

# Turn 2: Reference the information from Turn 1
USER_TURN_2 = "Based on what I told you, what career advice do you have for me? Also, what is my name?"

# -----------------------------------------------------------------------
# VARIANTS TO TRY IN CLASS (uncomment one at a time)
# -----------------------------------------------------------------------

# VARIANT A: Use a coding context instead of personal info
# USER_TURN_1 = "I am building a Python Flask API. I want to add JWT authentication to it."
# USER_TURN_2 = "Okay, now what library should I install for what we discussed?"

# VARIANT B: Use a number puzzle to make it starkly obvious
# USER_TURN_1 = "I'm thinking of the number 47. Remember it."
# USER_TURN_2 = "What number was I thinking of?"

# VARIANT C: Simulate a customer support session
# USER_TURN_1 = "My order number is #DK-99812. It hasn't arrived in 10 days."
# USER_TURN_2 = "Can you check the status for the order I just mentioned?"


# -----------------------------------------------------------------------
# RUN THE EXPERIMENT
# -----------------------------------------------------------------------

def run():
    print("\n" + "=" * 60)
    print("PART A: Two Separate API Calls (NO Shared History)")
    print("=" * 60)
    print("Watch what happens when we DON'T pass history between calls...\n")

    # --- Call 1: Introduce Aisha ---
    print(f"📤 CALL 1 — User says: \"{USER_TURN_1}\"\n")
    response_1 = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_TURN_1}
        ],
        model=MODEL,
    )
    reply_1 = response_1.choices[0].message.content
    print(f"🤖 AI replies: {reply_1}\n")

    # --- Call 2: Ask a follow-up — FRESH call, no history ---
    print(f"📤 CALL 2 — User says: \"{USER_TURN_2}\"")
    print(f"   ⚠️  Notice: we start FRESH. No memory of Call 1.\n")
    response_2 = client.chat.completions.create(
        messages=[
            # Completely new messages list — no mention of Aisha
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_TURN_2}
        ],
        model=MODEL,
    )
    reply_2 = response_2.choices[0].message.content
    print(f"🤖 AI replies: {reply_2}\n")

    print("─" * 60)
    print("❌ The model forgot Aisha entirely. Each call is a blank slate.")
    print("─" * 60)

    print("\n" + "=" * 60)
    print("PART B: Same Question — But Passing Full Conversation History")
    print("=" * 60)
    print("Now we pass the entire conversation in a single call...\n")

    # --- Call with FULL HISTORY ---
    print(f"📤 SENDING ONE CALL WITH FULL HISTORY...\n")
    response_3 = client.chat.completions.create(
        messages=[
            {"role": "system",    "content": SYSTEM_PROMPT},
            # Re-include Turn 1 as if it happened
            {"role": "user",      "content": USER_TURN_1},
            # Include the model's actual reply from Call 1 above
            {"role": "assistant", "content": reply_1},
            # Now ask Turn 2
            {"role": "user",      "content": USER_TURN_2}
        ],
        model=MODEL,
    )
    reply_3 = response_3.choices[0].message.content
    print(f"🤖 AI replies: {reply_3}\n")

    print("─" * 60)
    print("✅ It now remembers! Because we explicitly sent the history.")
    print("─" * 60)

    print("\n💡 KEY INSIGHT:")
    print("   ChatGPT does Part B behind the scenes on EVERY message you send.")
    print("   The 'memory' is not inside the model. It is inside the application layer.")
    print(f"\n📊 Token cost of including history: {response_3.usage.prompt_tokens} input tokens")
    print(f"   Token cost without history:      {response_1.usage.prompt_tokens} input tokens")
    print(f"   Extra tokens to 'remember':       +{response_3.usage.prompt_tokens - response_1.usage.prompt_tokens} tokens")


if __name__ == "__main__":
    run()
