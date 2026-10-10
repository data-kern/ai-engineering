"""
DataKern Session 5 Demo — Step 2: Query Rewriting (Context Condensation)
Transforms ambiguous multi-turn follow-ups into complete standalone queries
before retrieval using Groq (llama-3.1-8b-instant), matching Slides 8, 9, and 10.
"""

import os
from typing import List, Dict

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def rewrite_query(
    conversation_history: List[Dict[str, str]],
    latest_message: str,
    model: str = "llama-3.1-8b-instant"
) -> str:
    """
    Uses the LLM (Groq Llama 3.1 8B) to rewrite a follow-up message into a standalone query.
    conversation_history: [{"role": "user"|"assistant", "content": "..."}]

    Implements Slide 10 logic.
    """
    if not conversation_history:
        return latest_message

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "\n❌ [Authentication Error] GROQ_API_KEY is not set.\n"
            "   As taught in DataKern Session 5 (Slide 9 & 10), pre-retrieval query rewriting\n"
            "   requires an active LLM call via Groq.\n"
            "   Please export your key before running:\n"
            "     export GROQ_API_KEY=\"gsk_...\"\n"
        )

    if not GROQ_AVAILABLE:
        raise ImportError("groq package is not installed in the active environment. Run: pip install groq")

    # Format the last 4 turns (last 2 user/assistant cycles)
    history_text = "\n".join(
        f"{turn['role'].upper()}: {turn['content']}"
        for turn in conversation_history[-4:]
    )

    rewrite_prompt = (
        "You are an AI search query rewriter in an enterprise financial knowledge system.\n"
        "Given the conversation history below and the user's latest follow-up question,\n"
        "rewrite the latest question into a SINGLE complete, standalone search query\n"
        "that incorporates all relevant prior context (such as client risk tier, asset names, or topic).\n"
        "RULES:\n"
        "- Do NOT answer the question.\n"
        "- Do NOT output explanations or preamble.\n"
        "- Output ONLY the rewritten standalone question.\n\n"
        f"CONVERSATION HISTORY:\n{history_text}\n\n"
        f"LATEST FOLLOW-UP MESSAGE:\n{latest_message}\n\n"
        "STANDALONE REWRITTEN QUERY:"
    )

    try:
        client = Groq(api_key=api_key.strip())
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": rewrite_prompt}],
            max_tokens=100,
            temperature=0.0,
        )
        rewritten = response.choices[0].message.content.strip()
        # Clean any accidental wrapping quotes
        if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
            rewritten = rewritten[1:-1].strip()
        return rewritten
    except Exception as e:
        raise RuntimeError(f"Groq API error during query rewrite: {e}") from e
