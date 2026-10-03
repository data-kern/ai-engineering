#!/usr/bin/env python3
"""
scripts/03_rag_pipeline_walkthrough.py — The Full RAG Pipeline, Step by Step

Run this script BEFORE starting the service.
You do not need uvicorn. You do not need Docker.
You just need the database set up (scripts 01 and 02) and a Groq API key.

This script runs the complete RAG pipeline for one question and prints
what each step produces — so you can see exactly how the pipeline works,
not just its final output.

Prerequisites:
  python scripts/01_setup_vector_db.py
  python scripts/02_index_documents.py
  export GROQ_API_KEY="gsk_..."

Run from the demo/ folder:
  python scripts/03_rag_pipeline_walkthrough.py
"""

import os
import sys

# Add the demo/ directory to the path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import phoenix as px
    px.launch_app()
    print("\n[Phoenix] Trace UI available at: http://localhost:6006")
except Exception:
    pass

from app.step2_embed    import embed_text
from app.step3_search   import search_chunks
from app.step4_inject   import build_direct_prompt, build_rag_prompt
from app.step5_generate import call_llm

# Load client profile from data/client_profile.txt
def load_client_profile() -> str:
    profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "client_profile.txt")
    with open(profile_path, "r", encoding="utf-8") as f:
        return f.read().strip()

CLIENT_PROFILE = load_client_profile()
def pause():
    input("\n🔍 Press ENTER to continue ➔ ")
    print("\n" + "─" * 70)


def run_walkthrough(question: str) -> None:
    print("\n" + "=" * 70)
    print("  RAG PIPELINE WALKTHROUGH")
    print("  Apex Financial — Mr. Peterson (Conservative client)")
    print("=" * 70)

    # ── STEP 1: RECEIVE ───────────────────────────────────────────────────────
    print("\nSTEP 1 — RECEIVE the question")
    print(f"  Question: \"{question}\"")
    pause()

    # ── STEP 2: EMBED ─────────────────────────────────────────────────────────
    print("STEP 2 — EMBED the question")
    print("PREDICT: Before we can search the database, we must embed the question.")
    print("Will the question vector be the same dimension (384) as the document chunks?")
    pause()

    query_vector = embed_text(question)
    print(f"  ✅ Vector produced.")
    print(f"     Dimensions : {len(query_vector)}")
    print(f"     First 8 values: {[round(v, 4) for v in query_vector[:8]]}")
    pause()

    # ── STEP 3: SEARCH ────────────────────────────────────────────────────────
    print("STEP 3 — SEARCH pgvector for relevant policy chunks")
    print("PREDICT: How does pgvector know which chunks are 'most relevant'?")
    pause()
    
    print("  Answer: It uses cosine distance (similarity) between the question vector")
    print("  and all the chunk vectors in the database.")

    chunks = search_chunks(query_vector, top_k=3)
    print(f"\n  ✅ {len(chunks)} chunks retrieved from pgvector.\n")
    for i, chunk in enumerate(chunks):
        preview = chunk["chunk_text"][:200].replace("\n", " ")
        print(f"  Chunk {i + 1} (similarity: {chunk['similarity']:.4f}): {preview}...")
    pause()

    # ── STEP 4: INJECT ────────────────────────────────────────────────────────
    print("STEP 4 — INJECT — build the augmented system prompt")
    chunk_texts = [c["chunk_text"] for c in chunks]
    rag_prompt  = build_rag_prompt(CLIENT_PROFILE, chunk_texts)
    direct_prompt = build_direct_prompt(CLIENT_PROFILE)

    print("  Here is the EXACT prompt that will be sent to the LLM.")
    print("  ┌─ RAG SYSTEM PROMPT ──────────────────────────────────────────────────┐")
    for line in rag_prompt.strip().split("\n"):
        print(f"  │  {line}")
    print("  └──────────────────────────────────────────────────────────────────────┘")
    pause()

    # ── STEP 5: GENERATE ──────────────────────────────────────────────────────
    print("STEP 5 — GENERATE the answer")
    print("PREDICT: Will the LLM give the same answer with and without the policy context?")
    pause()

    print("  Generating RAG answer...")
    rag_answer = call_llm(rag_prompt, question)
    print(f"\n  ✅ RAG ANSWER:\n  {rag_answer.strip()}")
    
    print("\n  Generating DIRECT answer (no policy)...")
    direct_answer = call_llm(direct_prompt, question)
    print(f"\n  ✅ DIRECT ANSWER:\n  {direct_answer.strip()}")

    # ── CLEAN REFERENCE ───────────────────────────────────────────────────────
    pause()
    print("SECTION 6: The Clean Reference (The entire pipeline code)")
    print("""
    # This is all it takes to run a RAG pipeline once the data is indexed:
    
    from app.step2_embed import embed_text
    from app.step3_search import search_chunks
    from app.step4_inject import build_rag_prompt
    from app.step5_generate import call_llm

    def answer_question(question, client_profile):
        # 1. Embed the question
        query_vector = embed_text(question)
        
        # 2. Retrieve relevant chunks
        chunks = search_chunks(query_vector, top_k=3)
        chunk_texts = [c["chunk_text"] for c in chunks]
        
        # 3. Inject context into the prompt
        prompt = build_rag_prompt(client_profile, chunk_texts)
        
        # 4. Generate the answer
        return call_llm(prompt, question)
    """)

    print("\n" + "=" * 70)
    print("✅ Pipeline Walkthrough Complete!")
    print("OBSERVE: Open http://localhost:6006 to see these LLM calls traced in Phoenix.")
    print("\nNext → run python scripts/04_demo_comparison.py")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "Should Mr. Peterson add more NVDA to his portfolio?"

    run_walkthrough(question)
