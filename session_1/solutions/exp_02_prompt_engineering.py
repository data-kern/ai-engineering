"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 2: Prompt Engineering — Talking to the Model Like a Pro
=======================================================================

WHAT THIS DEMONSTRATES:
  The quality of your output is almost entirely determined by the quality
  of your input. This is the art and science of Prompt Engineering.

  Four techniques are shown here, in order of complexity:

  1. Zero-Shot     → Just ask. No examples. The baseline.
  2. Few-Shot      → Give examples first. Dramatic improvement on structured tasks.
  3. Chain-of-Thought → Ask it to "think step by step." Better reasoning.
  4. Output Format → Tell it exactly HOW to format the response (JSON, table, etc.)

THE ANALOGY:
  Going back to our expert in the room with no windows:
  A vague note gets a vague reply.
  A precise, well-structured note — with examples and clear expectations —
  gets a precise, well-structured reply.
  The expert hasn't changed. Only the quality of your note has.

INSTRUCTOR NOTES:
  → Run each technique ONE AT A TIME. After each run, ask:
     "What did we change in the prompt? How did the output change?"
  → The Few-Shot demo is the most visual — run it twice
     (once with no examples, once with examples) for a direct comparison.
  → The Chain-of-Thought demo works best on a reasoning/math task.
  → The Output Format demo is the most practically useful — JSON output
     is something every developer needs.

SETUP:
  pip install groq
  export GROQ_API_KEY="your_key_from_console.groq.com"
=======================================================================
"""

import os
import sys
import json
from groq import Groq

if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found. Run: export GROQ_API_KEY='your_key'\n")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


def _call(system: str, user: str, label: str = "") -> str:
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system.strip()},
            {"role": "user",   "content": user.strip()},
        ],
        model=MODEL,
    )
    text = resp.choices[0].message.content
    tokens = resp.usage.total_tokens
    print(f"\n{'─'*50}")
    if label:
        print(f"📌 {label}")
    print(f"{'─'*50}")
    print(text)
    print(f"{'─'*50}")
    print(f"📊 {tokens} tokens used\n")
    return text


# ===========================================================================
# TECHNIQUE 1: Zero-Shot — Just Ask. No Examples.
# ===========================================================================

def technique_1_zero_shot():
    """
    Zero-shot: Give the model a task with no examples or hints.
    This is the starting point — the baseline every other technique improves upon.
    """
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: Zero-Shot — Just Ask")
    print("=" * 60)
    print("We give the model a task with NO examples and NO special structure.")
    print("This is what most beginners do. Let's see what we get.\n")

    SYSTEM = "You are a helpful assistant."

    USER = """
    Classify the sentiment of this customer review as Positive, Negative, or Neutral.

    Review: "The delivery was late and the packaging was damaged, 
    but the product itself is exactly what I needed."
    """

    # -----------------------------------------------------------------------
    # VARIANTS TO TRY IN CLASS (uncomment one at a time)
    # -----------------------------------------------------------------------
    # VARIANT A: Try a more ambiguous review
    # USER = """
    # Classify the sentiment of this customer review as Positive, Negative, or Neutral.
    # Review: "It's fine, I guess. Does what it says on the box."
    # """

    # VARIANT B: Remove "as Positive, Negative, or Neutral" — see how it rambles
    # USER = """
    # Classify the sentiment of this customer review.
    # Review: "The product is great but customer service was awful."
    # """

    _call(SYSTEM, USER, label="Zero-Shot Result")

    print("💬 DISCUSS: What did it produce? Was the output structured or messy?")
    print("   How would you extract just the label in a real app?")


# ===========================================================================
# TECHNIQUE 2: Few-Shot — Give Examples, Then Ask
# ===========================================================================

def technique_2_few_shot():
    """
    Few-shot: Provide 2-3 worked examples in the prompt BEFORE asking your question.
    The model learns the PATTERN from the examples and applies it.

    This is one of the highest-value techniques for structured tasks.
    Run this AFTER zero-shot for a direct comparison.
    """
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: Few-Shot — Give Examples First")
    print("=" * 60)
    print("Same task. Same model. But now we show it EXACTLY what we want first.")
    print("Watch how the output changes.\n")

    SYSTEM = "You are a helpful assistant."

    USER = """
    Classify the sentiment of customer reviews. 
    Reply with ONLY a JSON object in this exact format: {"sentiment": "...", "confidence": "..."}
    
    Examples:
    
    Review: "Absolutely love this product! Best purchase I've made all year."
    {"sentiment": "Positive", "confidence": "High"}
    
    Review: "Terrible quality. Broke after two days. Avoid."
    {"sentiment": "Negative", "confidence": "High"}
    
    Review: "It arrived on time. Standard product, nothing special."
    {"sentiment": "Neutral", "confidence": "Medium"}
    
    Now classify this:
    
    Review: "The delivery was late and the packaging was damaged, 
    but the product itself is exactly what I needed."
    """

    # -----------------------------------------------------------------------
    # VARIANTS TO TRY IN CLASS (uncomment one at a time)
    # -----------------------------------------------------------------------
    # VARIANT A: Reduce to 1 example only — see if 1-shot is enough
    # (Remove 2 of the 3 examples from USER above)

    # VARIANT B: Change the output format to a different structure
    # USER = """
    # Classify sentiment. Reply only with:
    # SENTIMENT: [label] | REASON: [one sentence]
    #
    # Example:
    # Review: "Perfect, arrived early."
    # SENTIMENT: Positive | REASON: Customer received product faster than expected.
    #
    # Now classify this:
    # Review: "The delivery was late and the packaging was damaged,
    # but the product itself is exactly what I needed."
    # """

    result = _call(SYSTEM, USER, label="Few-Shot Result")

    # Bonus: Try to parse the JSON directly
    print("🔧 BONUS — Trying to parse the JSON output programmatically:")
    try:
        # Extract just the JSON part if there's extra text
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            print(f"   ✅ Parsed successfully!")
            print(f"   Sentiment:  {parsed.get('sentiment', 'N/A')}")
            print(f"   Confidence: {parsed.get('confidence', 'N/A')}")
    except Exception:
        print("   ⚠️  Could not parse as JSON. The model's output was not clean JSON.")
        print("       This is why output format control (Technique 4) matters so much.")

    print("\n💬 DISCUSS:")
    print("   Compare this to the Zero-Shot output. What's different?")
    print("   Could you use this output directly in a real application?")
    print("   In Zero-Shot, could you? What would you have to do differently?")


# ===========================================================================
# TECHNIQUE 3: Chain-of-Thought — Ask It to Think Before Answering
# ===========================================================================

def technique_3_chain_of_thought():
    """
    Chain-of-Thought (CoT): Instruct the model to show its reasoning
    before giving its final answer. Dramatically improves accuracy on
    tasks that require multi-step logic, math, or reasoning.

    The magic phrase: "Think step by step."
    """
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: Chain-of-Thought — Think Step by Step")
    print("=" * 60)
    print("We'll run the SAME logic problem twice:")
    print("  — Once directly (the model jumps to an answer)")
    print("  — Once with 'think step by step' (the model reasons first)")
    print()

    SYSTEM = "You are a helpful reasoning assistant."

    # ── Part A: Direct — no reasoning instruction ──
    DIRECT_USER = """
    A data engineering team has 5 members. Each member can process 3 datasets per day.
    The team needs to process 60 datasets. They've already processed 15.
    How many more days will the team need?
    """

    print("━━ PART A: Direct Question (no reasoning) ━━")
    _call(SYSTEM, DIRECT_USER, label="Direct Answer")

    # ── Part B: With Chain-of-Thought ──
    COT_USER = """
    A data engineering team has 5 members. Each member can process 3 datasets per day.
    The team needs to process 60 datasets. They've already processed 15.
    How many more days will the team need?

    Think step by step before giving your final answer.
    """

    print("━━ PART B: Same Question with Chain-of-Thought ━━")
    _call(SYSTEM, COT_USER, label="Chain-of-Thought Answer")

    # -----------------------------------------------------------------------
    # VARIANTS TO TRY IN CLASS
    # -----------------------------------------------------------------------
    # VARIANT A: Try a logic puzzle instead of math
    # DIRECT_USER = """
    # Alice is taller than Bob. Bob is taller than Carol.
    # Is Alice taller than Carol? Just say Yes or No.
    # """
    # COT_USER = DIRECT_USER + "\nThink step by step."

    # VARIANT B: Try a code debugging scenario
    # DIRECT_USER = """
    # This Python code raises a TypeError. What is wrong?
    # def add(a, b): return a + b
    # result = add("3", 4)
    # """
    # COT_USER = DIRECT_USER + "\nExplain your reasoning step by step."

    print("💬 DISCUSS:")
    print("   Did adding 'think step by step' change the answer?")
    print("   Did it change how CONFIDENT you feel about the answer?")
    print("   For what types of tasks would you always use Chain-of-Thought?")


# ===========================================================================
# TECHNIQUE 4: Output Format Control — Tell It Exactly What to Return
# ===========================================================================

def technique_4_output_format():
    """
    Output Format Control: Explicitly describe the exact format you want.
    
    In production apps, you almost never display raw LLM text to users.
    You parse it, store it in a database, or feed it to another system.
    The model MUST return structured data that your code can process.
    
    This technique is arguably the most practically important.
    """
    print("\n" + "=" * 60)
    print("TECHNIQUE 4: Output Format Control")
    print("=" * 60)
    print("We'll ask the model to extract information from unstructured text")
    print("and return it in a clean, machine-readable JSON format.\n")

    SYSTEM = """
    You are a data extraction assistant. 
    You extract structured information from unstructured text.
    
    You MUST return ONLY valid JSON. 
    Do NOT include any explanation, markdown formatting, or extra text.
    Return raw JSON only.
    """

    USER = """
    Extract the key information from this job posting and return it as JSON.
    
    Job Posting:
    "We are DataKern, a fast-growing AI education startup. We're looking for a 
    Senior AI Engineer to join our team remotely. You'll need 3+ years of experience 
    with Python, LLMs, and cloud platforms (AWS or Azure). The salary range is 
    €80,000–€110,000 per year. Applications close September 30th, 2026.
    Contact jobs@data-kern.com for questions."
    
    Required JSON structure:
    {
        "company": "",
        "role": "",
        "experience_required_years": 0,
        "skills": [],
        "location": "",
        "salary_min": 0,
        "salary_max": 0,
        "currency": "",
        "application_deadline": "",
        "contact_email": ""
    }
    """

    # -----------------------------------------------------------------------
    # VARIANTS TO TRY IN CLASS
    # -----------------------------------------------------------------------
    # VARIANT A: Extract from a customer support email
    # USER = """
    # Extract data from this support ticket as JSON with fields:
    # customer_name, issue_type, urgency (Low/Medium/High), product_mentioned.
    #
    # Ticket: "Hi, I'm Sarah Chen and I purchased the DataKern AI Masterclass
    # three days ago. I still can't access the course materials. I have an
    # important presentation in two days that depends on this content. Please help ASAP!"
    # """

    # VARIANT B: Ask for markdown table instead of JSON
    # SYSTEM = "You are a helpful formatting assistant."
    # USER = """
    # Format this data as a clean markdown table:
    # Models: GPT-4 (OpenAI, released Mar 2023, $0.03/1k tokens),
    # Claude 3 (Anthropic, released Mar 2024, $0.015/1k tokens),
    # Gemini Pro (Google, released Feb 2024, $0.00025/1k tokens)
    # """

    result = _call(SYSTEM, USER, label="Structured JSON Extraction")

    # Try to actually parse and use the JSON
    print("🔧 BONUS — Using the structured output in code:")
    try:
        data = json.loads(result)
        print(f"   ✅ Valid JSON! Here's how you'd USE it in your application:")
        print(f"   company   = {data.get('company')}")
        print(f"   role      = {data.get('role')}")
        print(f"   salary    = {data.get('currency')}{data.get('salary_min')}–{data.get('salary_max')}")
        print(f"   skills    = {data.get('skills')}")
        print(f"   deadline  = {data.get('application_deadline')}")
    except json.JSONDecodeError:
        print("   ⚠️  Output is not clean JSON. Common issue: the model added markdown ```json``` fencing.")
        print("       Fix: add 'Do not wrap in markdown code blocks' to the system prompt.")

    print("\n💬 DISCUSS:")
    print("   What would happen if you passed this raw JSON to a database?")
    print("   What if the model adds markdown fences around the JSON?")
    print("   How would you make this more robust in a production application?")


# ===========================================================================
# BONUS — Prompt Engineering Cheat Sheet (printed, not an experiment)
# ===========================================================================

def print_cheat_sheet():
    """Print a quick reference cheat sheet for the techniques covered."""
    print("\n" + "=" * 60)
    print("📋 PROMPT ENGINEERING CHEAT SHEET")
    print("=" * 60)
    print("""
  TECHNIQUE        WHEN TO USE                        MAGIC PHRASE
  ─────────────────────────────────────────────────────────────────
  Zero-Shot        Simple, direct tasks               [Just ask]
                   General Q&A, summaries

  Few-Shot         Structured/repeatable output       "Here are examples..."
                   Classification, extraction         + 2–3 examples before asking

  Chain-of-Thought Complex reasoning, math            "Think step by step."
                   Debugging, logic problems          "Explain your reasoning."

  Output Format    Any app that processes LLM output  "Return ONLY valid JSON."
                   APIs, databases, downstream code   + describe the schema

  Role/Persona     Specialized responses              "You are a [expert]..."
  (System Prompt)  Tone and style control             "Your rules are..."
  ─────────────────────────────────────────────────────────────────
  GOLDEN RULE: Vague prompt → Vague output.
               Specific prompt → Specific output.
               The model hasn't changed. Only your note has.
""")


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    # -----------------------------------------------------------------------
    # 👇 INSTRUCTOR: Uncomment ONE technique at a time during class.
    # -----------------------------------------------------------------------

    technique_1_zero_shot()
    # technique_2_few_shot()
    # technique_3_chain_of_thought()
    # technique_4_output_format()

    # --- Print the cheat sheet at the end of this experiment ---
    # print_cheat_sheet()
