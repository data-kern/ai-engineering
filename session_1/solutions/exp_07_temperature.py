"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 6: Temperature — Randomness, Creativity & Consistent Lies
=======================================================================

WHAT THIS DEMONSTRATES:
  Temperature is the most important parameter in LLM calls.
  It controls the RANDOMNESS of the model's output.

  temperature = 0.0  →  Deterministic. Same prompt = same answer (almost always).
                         Best for: factual Q&A, data extraction, structured output.

  temperature = 1.0  →  Creative & varied. Same prompt = different answer each time.
                         Best for: brainstorming, creative writing, chatbots.

  temperature > 1.0  →  Chaotic. The model starts making unusual token choices.
                         Rarely useful in practice.

THE CRITICAL INSIGHT:
  Low temperature does NOT mean ACCURATE. It means CONSISTENT.
  If the model is wrong at temperature=0, it will be WRONG THE SAME WAY
  every single time. Consistency ≠ Correctness.

INSTRUCTOR NOTES:
  → Run Part A TWICE (you'll see the same answer both times) → consistency demo
  → Run Part B TWICE (you'll see different answers) → randomness demo
  → Run Part C → the CRITICAL insight: temp=0 is still confidently wrong
  → This is a great segue into why you need evaluation — not just vibes

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

SYSTEM_PROMPT = "You are a helpful assistant."

# Part A: Factual question — run twice at temp=0
FACTUAL_PROMPT = "What is the capital of France? Answer in exactly one word."

# Part B: Creative question — run twice at temp=1.0
CREATIVE_PROMPT = "Write a 2-sentence description of a sunset. Be poetic and unique."

# Part C: Factual question about something FAKE — at temp=0 (should be consistently wrong)
FAKE_FACT_PROMPT = "What year did the Great Martian War of 2023 begin? Answer in one sentence."


# -----------------------------------------------------------------------
# VARIANTS TO TRY IN CLASS
# -----------------------------------------------------------------------

# VARIANT A: Try different temperatures on the same creative prompt
# Uncomment and change the temperature in the API call below

# VARIANT B: Ask for a JSON object — see how temperature affects structure
# CREATIVE_PROMPT = 'Return a JSON object with keys "name" and "hobby" for a fictional person.'

# VARIANT C: Code generation — does temperature matter?
# CREATIVE_PROMPT = "Write a Python function that returns the Fibonacci sequence up to n."


# -----------------------------------------------------------------------
# RUN THE EXPERIMENT
# -----------------------------------------------------------------------

def call(prompt, temperature, label=""):
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        model=MODEL,
        temperature=temperature,
    )
    return response.choices[0].message.content


def run():
    print("\n" + "=" * 60)
    print("PART A: temperature=0 — Deterministic (Run Twice)")
    print("=" * 60)
    print(f"📤 Question: {FACTUAL_PROMPT}\n")

    answer_a1 = call(FACTUAL_PROMPT, temperature=0.0)
    print(f"🤖 Run 1: {answer_a1}")

    answer_a2 = call(FACTUAL_PROMPT, temperature=0.0)
    print(f"🤖 Run 2: {answer_a2}")

    match = "✅ SAME" if answer_a1.strip() == answer_a2.strip() else "⚠️  DIFFERENT"
    print(f"\n   {match} — temperature=0 should be (near) identical each time.\n")


    print("=" * 60)
    print("PART B: temperature=1.0 — Creative (Run Twice)")
    print("=" * 60)
    print(f"📤 Question: {CREATIVE_PROMPT}\n")

    answer_b1 = call(CREATIVE_PROMPT, temperature=1.0)
    print(f"🤖 Run 1:\n{answer_b1}\n")

    answer_b2 = call(CREATIVE_PROMPT, temperature=1.0)
    print(f"🤖 Run 2:\n{answer_b2}\n")

    print("   Notice how the two answers are different — temperature=1.0 injects randomness.\n")


    print("=" * 60)
    print("PART C: temperature=0 on a FAKE fact — The Critical Insight")
    print("=" * 60)
    print(f"📤 Question: {FAKE_FACT_PROMPT}\n")
    print("   ⚠️  Remember: The Great Martian War of 2023 is FICTIONAL.\n")

    answer_c1 = call(FAKE_FACT_PROMPT, temperature=0.0)
    print(f"🤖 Run 1: {answer_c1}")

    answer_c2 = call(FAKE_FACT_PROMPT, temperature=0.0)
    print(f"🤖 Run 2: {answer_c2}")

    print("\n─" * 30)
    print("💥 KEY INSIGHT:")
    print("   The model hallucinated — and it did so CONSISTENTLY at temp=0.")
    print("   Low temperature does NOT equal accuracy.")
    print("   CONSISTENT WRONG ANSWER ≠ CORRECT ANSWER.")
    print("   This means 'run it again to double-check' is NOT a valid strategy.")
    print("─" * 30)

    print("\n💡 TEMPERATURE CHEAT SHEET:")
    print("   0.0       → Factual Q&A, structured output, data extraction")
    print("   0.3–0.7   → Balanced: friendly chatbots, summarization")
    print("   0.8–1.0   → Creative writing, brainstorming, ideation")
    print("   > 1.0     → Experimental / rarely production-useful")


if __name__ == "__main__":
    run()
