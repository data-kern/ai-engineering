"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 3: Knowledge Cut-off — The Model Is Frozen in Time
=======================================================================

WHAT THIS DEMONSTRATES:
  LLMs are trained on a fixed dataset collected up to a specific date
  (the "knowledge cut-off"). After that date, the model knows nothing
  about what happened in the world — unless you explicitly tell it.

  This is fundamentally different from a search engine. A search engine
  fetches live data. An LLM plays back a snapshot of the past.

THE ANALOGY:
  Imagine hiring a brilliant expert who spent 5 years reading every book,
  article, and paper ever written — but then went into a coma.
  They wake up today. They know EVERYTHING up to when they went under.
  But they have no idea what happened while they were asleep.

INSTRUCTOR NOTES:
  → Ask: "What happens if you ask about something that happened AFTER the cut-off?"
  → The model might: (a) admit it doesn't know (good!), or (b) hallucinate (bad!)
  → This sets up a natural bridge to RAG (Retrieval-Augmented Generation)
     which you'll cover in a later session.

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
# PROMPTS — Edit these to experiment during class
# -----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a helpful, honest AI assistant.
When you don't know something or when your information may be outdated,
say so clearly rather than guessing. Be specific about your knowledge limitations.
"""

USER_PROMPT = """
What were the top 3 most important AI news stories from the past 7 days?
Please include the exact dates, the companies involved, and the key announcements.
"""

# -----------------------------------------------------------------------
# VARIANTS TO TRY IN CLASS (uncomment one at a time)
# -----------------------------------------------------------------------

# VARIANT A: Ask what its cut-off date actually is
# USER_PROMPT = "What is your training data cut-off date? What is the most recent event you know about?"

# VARIANT B: Ask about a specific recent software release
# USER_PROMPT = "What are the new features in the latest version of Python released this month?"

# VARIANT C: Ask about a current financial/market event
# USER_PROMPT = "What is the current price of Bitcoin right now? What happened to its price this week?"

# VARIANT D: Ask something where cut-off matters for safety (medical / legal)
# USER_PROMPT = """
# What are the current EU AI Act regulations that companies must comply with RIGHT NOW?
# What are the exact deadlines and fine amounts?
# """

# VARIANT E: Contrast with a timeless question (no cut-off issue)
# USER_PROMPT = "Explain how the TCP/IP protocol works. Include the 4 layers."


# -----------------------------------------------------------------------
# RUN THE EXPERIMENT
# -----------------------------------------------------------------------

def run():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user",   "content": USER_PROMPT.strip()}
    ]

    print("\n📤 SENDING REQUEST...")
    print(f"   Asking about VERY RECENT events (the model may not know)...\n")

    response = client.chat.completions.create(
        messages=messages,
        model=MODEL,
    )

    ai_response = response.choices[0].message.content

    print("🤖 AI RESPONSE:")
    print("─" * 50)
    print(ai_response)
    print("─" * 50)

    print("\n💡 ANALYSIS:")
    print("   Did the model: (a) admit it doesn't know, or (b) invent specific dates/events?")
    print("   If (b): that's HALLUCINATION layered on top of a CUT-OFF limitation.")
    print("   If (a): that's actually the CORRECT, honest behavior — but it means your app is useless")
    print("           for any question about current events unless you inject real-time data.")
    print(f"\n📊 USAGE: {response.usage.prompt_tokens} input + {response.usage.completion_tokens} output tokens")


if __name__ == "__main__":
    run()
