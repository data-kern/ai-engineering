"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 1: The Basic Call — "Hello World" for AI Engineering
=======================================================================

WHAT THIS DEMONSTRATES:
  The anatomy of an LLM API call:
    - System Prompt  → The developer's voice (instructions, persona, rules)
    - User Prompt    → The user's input / question
    - Roles          → 'system', 'user', 'assistant'
    - Response       → Navigating the response object to get the text

INSTRUCTOR NOTES:
  → Run this FIRST. Let the dopamine hit. It works. It's magic.
  → Walk through each part slowly. Point to the terminal output.
  → After the basic run, let STUDENTS try the variants below.

SETUP:
  pip install groq
  export GROQ_API_KEY="your_key_from_console.groq.com"
=======================================================================
"""

import os
import sys
from groq import Groq

# -----------------------------------------------------------------------
# Guard: Check for API key before anything else
# -----------------------------------------------------------------------
if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found.")
    print("   Run: export GROQ_API_KEY='your_key'")
    print("   Get a free key at: https://console.groq.com/keys\n")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


# -----------------------------------------------------------------------
# PROMPTS — Edit these to experiment during class
# -----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a friendly programming instructor at DataKern.
Keep your answers concise and simple — your students are absolute beginners.
Use one real-world analogy to explain every technical concept.
"""

USER_PROMPT = """
What's the capital of Australia?
"""

# -----------------------------------------------------------------------
# VARIANTS TO TRY IN CLASS (uncomment one at a time)
# -----------------------------------------------------------------------

# VARIANT A: Change the persona in the system prompt
# SYSTEM_PROMPT = "You are a grumpy medieval wizard who reluctantly teaches programming."

# VARIANT B: Ask in a different language
# USER_PROMPT = "¿Qué es una variable? Explícalo de forma simple."

# VARIANT C: Remove the system prompt entirely — what happens?
# SYSTEM_PROMPT = ""   # ← Try this and see how the model behaves without instructions

# VARIANT D: Ask something completely off-topic for this persona
# USER_PROMPT = "What is the best pizza topping?"


# -----------------------------------------------------------------------
# RUN THE EXPERIMENT
# -----------------------------------------------------------------------

def run():
    messages = [
        {
            "role": "system",
            # ↑ This is YOUR voice as the developer.
            # It tells the model who it is and how to behave.
            # Users never see this. It runs silently behind every request.
            "content": SYSTEM_PROMPT.strip()
        },
        {
            "role": "user",
            # ↑ This is what the end-user typed or asked.
            "content": USER_PROMPT.strip()
        }
    ]

    print("\n📤 SENDING REQUEST...")
    print(f"   Model: {MODEL}")
    print(f"   System: {SYSTEM_PROMPT.strip()[:80]}...")
    print(f"   User:   {USER_PROMPT.strip()}\n")

    response = client.chat.completions.create(
        messages=messages,
        model=MODEL,
    )

    # The API returns a complex object. We navigate it to get the text.
    #   response.choices        → list of possible responses (usually 1)
    #   response.choices[0]     → the first (and usually only) response
    #   .message.content        → the actual text
    ai_response = response.choices[0].message.content

    print("🤖 AI RESPONSE:")
    print("─" * 50)
    print(ai_response)
    print("─" * 50)

    # ↓ Token info — we'll explore this more in Experiment 7
    print(f"\n📊 USAGE:")
    print(f"   Input tokens:  {response.usage.prompt_tokens}")
    print(f"   Output tokens: {response.usage.completion_tokens}")
    print(f"   Total tokens:  {response.usage.total_tokens}")


if __name__ == "__main__":
    run()
