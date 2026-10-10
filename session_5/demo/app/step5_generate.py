"""
DataKern Session 5 Demo — Step 5: LLM Generation & Observability
Invokes Groq Llama 3.1 8B with real API execution and latency tracking (Slide 10 & 17).
No mock/simulated generation fallbacks — we execute real inference.
"""

import os
import time
from typing import Dict, Any

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def call_llm(
    prompt: str,
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.0,
    max_tokens: int = 400
) -> Dict[str, Any]:
    """
    Calls Groq API with llama-3.1-8b-instant and tracks execution latency.

    Raises:
        ValueError: If GROQ_API_KEY is missing.
        RuntimeError: If the Groq API call fails.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "\n❌ [Authentication Error] GROQ_API_KEY is not set.\n"
            "   As taught in DataKern Session 5, LLM generation requires an active Groq API key.\n"
            "   Please export your key before running:\n"
            "     export GROQ_API_KEY=\"gsk_...\"\n"
            "   (Get a free key at https://console.groq.com)\n"
        )

    if not GROQ_AVAILABLE:
        raise ImportError("groq package is not installed in the active environment. Run: pip install groq")

    start_time = time.time()
    try:
        client = Groq(api_key=api_key.strip())
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        content = response.choices[0].message.content.strip()
        return {
            "content": content,
            "latency_ms": elapsed_ms,
            "model": model,
            "mode": "live_groq",
        }
    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        raise RuntimeError(f"Groq API error during generation (after {elapsed_ms}ms): {e}") from e
