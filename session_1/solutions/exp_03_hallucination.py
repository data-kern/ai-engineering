"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 2: Hallucination — The Model Confidently Lies
=======================================================================

WHAT THIS DEMONSTRATES:
  LLMs do not "look things up." They predict the most statistically
  likely next token based on their training data.
  
  If a plausible-sounding answer exists in the "shape" of the training
  data — even for a FAKE topic — the model will generate it confidently
  without any warning.

  This is called HALLUCINATION. The model is not lying intentionally.
  It literally cannot distinguish real from fake. It just predicts text.

INSTRUCTOR NOTES:
  → Ask students to read the response carefully. Does it sound believable?
  → Ask: "Would a non-expert know this was wrong?"
  → Do NOT reveal upfront that The Great Martian War of 2023 is fake.
     Let them read the response first, then tell them.
  → Then try the Variant: ask it about a REAL event. Compare tone/confidence.

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
You are a knowledgeable history professor who specializes in modern world events.
Provide detailed, academic-quality summaries of historical events.
"""

USER_PROMPT = """
Tell me about The Great Martian War of 2023.
Give me a detailed summary: what caused it, which nations were involved,
and what were the key outcomes?
"""

# -----------------------------------------------------------------------
# VARIANTS TO TRY IN CLASS (uncomment one at a time)
# -----------------------------------------------------------------------

# VARIANT A: Ask about a real event — compare the response style
# USER_PROMPT = "Tell me about the 2008 global financial crisis. What caused it and what were the key outcomes?"

# VARIANT B: Ask it to cite sources — see if the citations are real
# USER_PROMPT = """
# Tell me about The Great Martian War of 2023.
# Please cite 3 academic papers or news articles that I can verify.
# """

# VARIANT C: Ask a very specific factual question about a fake person
# USER_PROMPT = "What were the major contributions of Dr. Elena Vostrikova to quantum biology? She published heavily in 2019-2021."

# VARIANT D: Ask for statistics about the fake event
# USER_PROMPT = "How many casualties were there in The Great Martian War of 2023? Give me precise figures by country."


# -----------------------------------------------------------------------
# RUN THE EXPERIMENT
# -----------------------------------------------------------------------

def run():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user",   "content": USER_PROMPT.strip()}
    ]

    print("\n📤 SENDING REQUEST...")
    print(f"   Topic: The Great Martian War of 2023 (⚠️ THIS NEVER HAPPENED)")
    print(f"   Watch how confidently the model responds...\n")

    response = client.chat.completions.create(
        messages=messages,
        model=MODEL,
    )

    ai_response = response.choices[0].message.content

    print("🤖 AI RESPONSE:")
    print("─" * 50)
    print(ai_response)
    print("─" * 50)

    print("\n⚠️  REVEAL: The Great Martian War of 2023 is COMPLETELY FICTIONAL.")
    print("   The model did not say 'I don't know.' It produced a confident narrative.")
    print("   This is HALLUCINATION — and it is one of the biggest risks in production LLM apps.")
    print(f"\n📊 USAGE: {response.usage.prompt_tokens} input + {response.usage.completion_tokens} output tokens")


if __name__ == "__main__":
    run()
