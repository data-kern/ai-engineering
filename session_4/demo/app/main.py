"""
main.py — FastAPI service: /ask and /ask/rag endpoints

This file wires the RAG pipeline to HTTP endpoints.
The pipeline logic lives in app/pipeline.py — read that first.

Two endpoints:
  POST /ask       → run_direct()  — no retrieval, LLM training knowledge only
  POST /ask/rag   → run_rag()     — embed → search → inject → generate

GET /health → health check (used by Kubernetes liveness probes)

The demo client profile is hardcoded here so the service is self-contained.
"""

from fastapi import FastAPI, HTTPException

from app.schema   import QuestionRequest, AnswerResponse
from app.pipeline import run_direct, run_rag

# ─────────────────────────────────────────────────────────────────────────────
# Phoenix observability — optional, non-blocking
# If Phoenix is not installed or has a port conflict, the service still starts.
# Open http://localhost:6006 to see LLM call traces when it is running.
# ─────────────────────────────────────────────────────────────────────────────
try:
    import phoenix as px
    px.launch_app()
    print("[Phoenix] Trace UI available at: http://localhost:6006")
except Exception as exc:
    print(f"[Phoenix] Could not start — observability disabled. ({exc})")

app = FastAPI(
    title="Session 4 RAG Demo — Apex Financial",
    description=(
        "Demonstrates the difference between a direct LLM call (no policy context) "
        "and a RAG-augmented call (with retrieved policy chunks).\n\n"
        "**Try the same question on both endpoints and compare the answers.**\n\n"
        "See the full pipeline step by step: run `python scripts/03_rag_pipeline_walkthrough.py`"
    ),
    version="4.0.0",
)

import os

# ─────────────────────────────────────────────────────────────────────────────
# Demo client profile — Mr. Peterson is a Conservative client.
# The NVDA question produces a clearly wrong answer from /ask (no policy)
# and a compliant answer from /ask/rag (with retrieved policy).
# ─────────────────────────────────────────────────────────────────────────────
def load_client_profile() -> str:
    profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "client_profile.txt")
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Error: Client profile not found at data/client_profile.txt."

DEMO_CLIENT_PROFILE = load_client_profile()

# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Health probe. Returns 200 OK when the service is ready."""
    return {"status": "healthy"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /ask — Direct LLM, no policy retrieval
# Shows what goes wrong when private context is missing.
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/ask", response_model=AnswerResponse)
def ask_direct_endpoint(request: QuestionRequest):
    """
    Ask the LLM WITHOUT any policy context.

    The LLM answers from its general training knowledge only.
    It has no information about Apex Financial's Conservative client rules.

    Try: "Should Mr. Peterson add more NVDA to his portfolio?"
    Expected: generic advice that violates Conservative restrictions.
    """
    try:
        result = run_direct(
            question=       request.question,
            client_profile= DEMO_CLIENT_PROFILE,
        )
        return AnswerResponse(
            question=        result.question,
            answer=          result.answer,
            mode=            "direct — NO policy context (LLM training knowledge only)",
            chunks_used=     [],
            retrieved_count= 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# POST /ask/rag — RAG pipeline: embed → search → inject → generate
# Shows the solution: the LLM answers with retrieved policy context.
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/ask/rag", response_model=AnswerResponse)
def ask_rag_endpoint(request: QuestionRequest):
    """
    Ask the LLM WITH retrieved policy context.

    Pipeline:
      1. Embed the question → 384-float vector
      2. Search pgvector for the 3 most relevant policy chunks
      3. Inject those chunks into the system prompt
      4. Call the LLM with the augmented prompt

    Try: "Should Mr. Peterson add more NVDA to his portfolio?"
    Expected: a refusal citing the specific Conservative client rule.

    See `chunks_used` in the response to read the exact policy sections retrieved.
    """
    try:
        result = run_rag(
            question=       request.question,
            client_profile= DEMO_CLIENT_PROFILE,
            top_k=          3,
        )
        return AnswerResponse(
            question=        result.question,
            answer=          result.answer,
            mode=            "rag — WITH retrieved policy context",
            chunks_used=     [c["chunk_text"] for c in result.chunks_used],
            retrieved_count= result.retrieved_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
