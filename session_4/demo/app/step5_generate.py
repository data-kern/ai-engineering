"""
step5_generate.py — Pipeline Step 5: Generate the Answer

Sends the system prompt (built in Step 4) and the user's question
to the Groq LLM and returns the generated answer as a string.

The quality of the answer depends entirely on the system prompt:
  build_direct_prompt() → generic answer (no policy rules)
  build_rag_prompt()    → compliant answer (policy rules injected)

The model, temperature, and token limit are fixed in both modes.
The ONLY variable is the content of the system prompt.

This makes the comparison between /ask and /ask/rag a clean A/B test:
same question, same model, same settings — different prompt → different answer.

Usage:
    from app.step5_generate import call_llm

    answer = call_llm(system_prompt, "Should Mr. Peterson buy NVDA?")
    # → "I cannot recommend adding NVDA to Mr. Peterson's portfolio..."
"""

import os
from groq import Groq
from openinference.instrumentation.groq import GroqInstrumentor

GroqInstrumentor().instrument()

MODEL       = "openai/gpt-oss-120b"
TEMPERATURE = 0.1   # low temperature = consistent, deterministic answers
MAX_TOKENS  = 512


def _get_client() -> Groq:
    """Create the Groq API client from the GROQ_API_KEY environment variable."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set.\n"
            "Set it with: export GROQ_API_KEY='gsk_your_key_here'\n"
            "Get a free key at: https://console.groq.com"
        )
    return Groq(api_key=api_key)


def call_llm(system_prompt: str, question: str) -> str:
    """
    Send a system prompt + question to the LLM and return the answer.

    Args:
        system_prompt: The full system prompt, built by step4_inject.
                       Either build_direct_prompt() or build_rag_prompt().
        question:      The user's question string.

    Returns:
        The LLM's generated text response.

    The LLM receives two messages:
      {"role": "system", "content": system_prompt}  ← the rules + client info
      {"role": "user",   "content": question}        ← the question
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content
