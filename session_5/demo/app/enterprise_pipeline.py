"""
DataKern Session 5 Demo — Enterprise RAG Orchestrator Pipeline
Wires all 5 enterprise enhancements into an observable, production-grade flow:
  1. Input Sanitization (Defense 2)
  2. Multi-Turn Query Rewriting (Context Condensation)
  3. Security-Scoped Hybrid Search (pgvector + FTS + RRF)
  4. Structural Prompt Assembly (Defense 1 & 3)
  5. LLM Generation with Latency & Phoenix Tracing
"""

import os
import time
from typing import Dict, Any, List, Optional

from app.schema import EnterpriseRAGRequest, EnterpriseRAGResponse, ChunkResult
from app.step1_sanitize import scan_for_injection, sanitize_or_quarantine
from app.step2_rewrite import rewrite_query
from app.step3_hybrid_search import search_enterprise_chunks
from app.step4_inject_secure import build_secure_rag_prompt
from app.step5_generate import call_llm

DEFAULT_CLIENT_PROFILE = """Client Name: Harold Peterson
Risk Category: Conservative
Account ID: APEX-7821
Mandate: Capital preservation and income distribution. Equity exposure capped strictly per policy."""


def run_enterprise_rag(
    request: EnterpriseRAGRequest,
    client_profile: str = DEFAULT_CLIENT_PROFILE,
    conn = None
) -> EnterpriseRAGResponse:
    """
    Executes the full Enterprise RAG request.
    """
    latencies = {}

    # ── STAGE 1: Input Sanitization ──────────────────────────────────────────
    t0 = time.time()
    flagged, triggers = scan_for_injection(request.message)
    sanitized_message = request.message
    if flagged and request.sanitize_input:
        sanitized_message, _, _ = sanitize_or_quarantine(request.message, quarantine=False)
    latencies["sanitization_ms"] = round((time.time() - t0) * 1000, 2)

    # ── STAGE 2: Query Rewriting ─────────────────────────────────────────────
    t0 = time.time()
    history_dicts = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    was_rewritten = len(history_dicts) > 0
    if was_rewritten:
        standalone_query = rewrite_query(history_dicts, sanitized_message)
    else:
        standalone_query = sanitized_message
    latencies["query_rewriting_ms"] = round((time.time() - t0) * 1000, 2)

    # ── STAGE 3: Access-Scoped Hybrid RRF Retrieval ──────────────────────────
    t0 = time.time()
    search_mode = "hybrid" if request.use_hybrid else "vector"
    user_tier = request.user_context.access_tier if request.user_context else 1

    raw_chunks = search_enterprise_chunks(
        query_text=standalone_query,
        user_tier=user_tier,
        top_k=request.top_k,
        chunk_strategy=request.chunk_strategy,
        mode=search_mode,
        conn=conn
    )
    latencies["retrieval_ms"] = round((time.time() - t0) * 1000, 2)

    # Convert to ChunkResult models
    chunk_models = [
        ChunkResult(
            id=c.get("id", 0),
            doc_title=c.get("doc_title", "Unknown"),
            access_tier=c.get("access_tier", 1),
            chunk_text=c.get("chunk_text", ""),
            vector_rank=c.get("vector_rank"),
            keyword_rank=c.get("keyword_rank"),
            rrf_score=c.get("rrf_score", 0.0)
        )
        for c in raw_chunks
    ]

    # Check retrieved chunks for injection attempts (Slide 13)
    chunk_flagged = False
    for c in raw_chunks:
        c_flagged, _ = scan_for_injection(c.get("chunk_text", ""))
        if c_flagged:
            chunk_flagged = True
            break

    # ── STAGE 4: Secure Prompt Assembly ──────────────────────────────────────
    t0 = time.time()
    secure_prompt = build_secure_rag_prompt(
        client_profile=client_profile,
        chunks=raw_chunks,
        user_query=sanitized_message,
        enable_defense=True
    )
    latencies["prompt_assembly_ms"] = round((time.time() - t0) * 1000, 2)

    # ── STAGE 5: LLM Generation ──────────────────────────────────────────────
    t0 = time.time()
    llm_result = call_llm(secure_prompt)
    latencies["llm_generation_ms"] = llm_result.get("latency_ms", round((time.time() - t0) * 1000, 2))
    latencies["total_pipeline_ms"] = round(sum(latencies.values()), 2)

    security_notes = None
    if flagged:
        security_notes = f"User prompt flagged for injection triggers: {triggers}"
    elif chunk_flagged:
        security_notes = "Retrieved document chunk contained adversarial injection markers; structural defense active."

    return EnterpriseRAGResponse(
        answer=llm_result["content"],
        rewritten_query=standalone_query if was_rewritten else None,
        was_rewritten=was_rewritten,
        retrieved_chunks=chunk_models,
        security_flagged=(flagged or chunk_flagged),
        security_notes=security_notes,
        latency_breakdown_ms=latencies
    )
