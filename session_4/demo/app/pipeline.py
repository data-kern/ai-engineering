"""
pipeline.py — The RAG Pipeline Orchestrator

Read this file first. It shows the full RAG flow in one place.

The pipeline has five steps. Two modes share most of them:

                    DIRECT mode        RAG mode
                    ───────────        ────────
  Step 1: Receive   question      →   question
  Step 2: Embed     (skipped)         question → 384-float vector
  Step 3: Search    (skipped)         vector → top 3 policy chunks
  Step 4: Inject    direct prompt →   rag prompt (chunks embedded)
  Step 5: Generate  LLM call     →   LLM call (same model, same settings)

The difference in the answer comes entirely from Step 4:
  DIRECT: the prompt has no policy context → LLM uses training knowledge
  RAG:    the prompt contains retrieved policy rules → LLM applies them

Usage:
    from app.pipeline import run_direct, run_rag

    result = run_rag(question, client_profile)
    print(result.answer)
    print(result.system_prompt)   # ← print this to see what the LLM received
    print(result.chunks_used)     # ← the retrieved policy chunks + scores
"""

from dataclasses import dataclass, field

from app.step2_embed    import embed_text
from app.step3_search   import search_chunks
from app.step4_inject   import build_direct_prompt, build_rag_prompt
from app.step5_generate import call_llm


@dataclass
class PipelineResult:
    """The output of one pipeline run — holds everything for inspection."""
    question:        str
    answer:          str
    mode:            str               # "direct" or "rag"
    system_prompt:   str               # the exact prompt sent to the LLM
    chunks_used:     list[dict] = field(default_factory=list)   # from step3
    retrieved_count: int = 0


def run_direct(question: str, client_profile: str) -> PipelineResult:
    """
    Run the direct pipeline — no retrieval, no policy injection.

    Active steps: 1 → 4 (direct prompt) → 5
    Skipped steps: 2 (embed), 3 (search)

    Args:
        question:       The advisor's question.
        client_profile: The client's name, risk category, and holdings.

    Returns:
        PipelineResult with the LLM's answer and the prompt that was sent.
    """
    # Step 4: Build prompt — no policy chunks
    system_prompt = build_direct_prompt(client_profile)

    # Step 5: Generate
    answer = call_llm(system_prompt, question)

    return PipelineResult(
        question=        question,
        answer=          answer,
        mode=            "direct",
        system_prompt=   system_prompt,
        chunks_used=     [],
        retrieved_count= 0,
    )


def run_rag(question: str, client_profile: str, top_k: int = 3) -> PipelineResult:
    """
    Run the full RAG pipeline — embed, search, inject, generate.

    Active steps: 1 → 2 → 3 → 4 (rag prompt) → 5

    Args:
        question:       The advisor's question.
        client_profile: The client's name, risk category, and holdings.
        top_k:          How many policy chunks to retrieve (default: 3).

    Returns:
        PipelineResult with the LLM's answer, the augmented prompt,
        and the retrieved policy chunks (with similarity scores).
    """
    # Step 2: Embed the question → 384-float vector
    query_vector = embed_text(question)

    # Step 3: Search pgvector for the most similar policy chunks
    chunks = search_chunks(query_vector, top_k=top_k)
    chunk_texts = [c["chunk_text"] for c in chunks]

    # Step 4: Build the augmented prompt — inject the retrieved chunks
    system_prompt = build_rag_prompt(client_profile, chunk_texts)

    # Step 5: Generate the answer
    answer = call_llm(system_prompt, question)

    return PipelineResult(
        question=        question,
        answer=          answer,
        mode=            "rag",
        system_prompt=   system_prompt,
        chunks_used=     chunks,
        retrieved_count= len(chunks),
    )
