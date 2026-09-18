"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 2: Prompt Engineering — Talking to the Model Like a Pro
=======================================================================

YOUR TASK:
  Implement 4 different Prompt Engineering techniques to see how the 
  quality of your prompt dictates the quality of the output.
=======================================================================
"""

import os
import sys
import json
from groq import Groq

if not os.environ.get("GROQ_API_KEY"):
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
    print(f"\n📌 {label}\n{'─'*50}\n{text}\n{'─'*50}")
    return text


def technique_1_zero_shot():
    print("\nTECHNIQUE 1: Zero-Shot — Just Ask")

    # TODO: Step 1 - Zero-Shot Prompt
    # System: "You are a helpful assistant."
    # User: "Classify the sentiment of this customer review as Positive, Negative, or Neutral: 'The delivery was late but the product is exactly what I needed.'"
    SYSTEM = """"""
    USER = """"""

    # _call(SYSTEM, USER, label="Zero-Shot Result")

    # VARIANTS TO TRY:
    # A. Remove "as Positive, Negative, or Neutral" from the prompt. Notice how the AI rambles instead of classifying.


def technique_2_few_shot():
    print("\nTECHNIQUE 2: Few-Shot — Give Examples First")

    # TODO: Step 2 - Few-Shot Prompt
    # System: "You are a helpful assistant."
    # User: You want it to reply with ONLY JSON: {"sentiment": "...", "confidence": "..."}
    # Provide 3 examples of reviews and their expected JSON output BEFORE giving it the final target review.
    SYSTEM = """"""
    USER = """"""

    # result = _call(SYSTEM, USER, label="Few-Shot Result")
    
    # VARIANTS TO TRY:
    # A. Reduce to 1 example. Does the AI still understand the pattern?
    # B. Change the requested format from JSON to a custom string like "SENTIMENT: [label] | REASON: [reason]"


def technique_3_chain_of_thought():
    print("\nTECHNIQUE 3: Chain-of-Thought — Think Step by Step")
    SYSTEM = "You are a helpful reasoning assistant."

    # TODO: Step 3 - Chain of Thought
    # User: "A data engineering team has 5 members. Each processes 3 datasets per day. They need 60 datasets. They've done 15. How many days are left?"
    # Add the magic phrase: "Think step by step before giving your final answer."
    USER = """"""

    # _call(SYSTEM, USER, label="Chain-of-Thought Answer")
    
    # VARIANTS TO TRY:
    # A. Remove the "Think step by step" phrase. Notice if the model gets the math wrong or right, and how it explains it.


def technique_4_output_format():
    print("\nTECHNIQUE 4: Output Format Control")

    # TODO: Step 4 - Strict Output Formatting
    # System: "You extract information. Return ONLY valid JSON. No markdown, no explanations."
    # User: Ask it to extract 'company', 'role', 'salary_min', 'salary_max' from a mock job posting. Provide the raw text of a job posting.
    SYSTEM = """"""
    USER = """"""

    # _call(SYSTEM, USER, label="Structured JSON Extraction")
    
    # VARIANTS TO TRY:
    # A. Ask for the output as a Markdown table instead of JSON.


if __name__ == "__main__":
    technique_1_zero_shot()
    # technique_2_few_shot()
    # technique_3_chain_of_thought()
    # technique_4_output_format()
