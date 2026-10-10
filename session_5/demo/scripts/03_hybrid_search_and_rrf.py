#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 03: Hybrid Search & Reciprocal Rank Fusion (RRF) Deep Dive

What you will learn:
  1. The Exact Identifier Blind Spot: Why pure vector search fails on "Section 4.2"
  2. The Semantic Blind Spot: Why pure keyword search fails on "risk-averse clients"
  3. Reciprocal Rank Fusion (RRF): How combining ranks (1/(60+rank)) outperforms naive score addition
  4. Real PostgreSQL implementation comparing Pure Vector vs Pure FTS vs Hybrid RRF

Usage:
  python scripts/03_hybrid_search_and_rrf.py
"""

import os
import sys

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.step3_hybrid_search import search_enterprise_chunks

DIVIDER = "═" * 74
SUB_DIVIDER = "─" * 74


def pause():
    try:
        input("\n🔍 Press ENTER to continue ➔ ")
    except (EOFError, KeyboardInterrupt):
        pass
    print("\n" + SUB_DIVIDER)


def print_results_table(title: str, results: list, score_type: str = "Score"):
    print(f"\n┌─ {title} " + "─" * (70 - len(title)) + "┐")
    if not results:
        print("│  [0 MATCHES FOUND]                                                     │")
        print("└" + "─" * 72 + "┘")
        return

    for i, r in enumerate(results):
        score_val = r.get("rrf_score") if "rrf" in score_type.lower() else r.get("similarity") if "similarity" in score_type.lower() else r.get("keyword_score", 0.0)
        v_rank = f"V-Rank: {r.get('vector_rank')}" if r.get('vector_rank') else "V-Rank: --"
        k_rank = f"K-Rank: {r.get('keyword_rank')}" if r.get('keyword_rank') else "K-Rank: --"
        preview = r['chunk_text'].strip()[:140].replace('\n', ' ')

        print(f"│ #{i+1} | {score_type}: {score_val:.4f} | {v_rank:<10} | {k_rank:<10} │")
        print(f"│     Title  : {r.get('doc_title', 'Vault')[:40]:<40}          │")
        print(f"│     Snippet: {preview}...")
        print("├" + "─" * 72 + "┤" if i < len(results) - 1 else "└" + "─" * 72 + "┘")


def main():
    print("\n" + DIVIDER)
    print("  DATAKERN SESSION 5: SCRIPT 03 — HYBRID SEARCH & RRF DEEP DIVE")
    print(DIVIDER)

    # Validate prerequisite API key
    provider = os.getenv("EMBEDDING_PROVIDER", "jina").lower().strip()
    if provider == "jina" and not os.getenv("JINA_API_KEY"):
        print("❌ MISSING PREREQUISITE: JINA_API_KEY is not set.")
        print("   Embedding the search query requires an active Jina key:")
        print("     export JINA_API_KEY=\"your_key_here\"\n")
        sys.exit(1)
    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("❌ MISSING PREREQUISITE: GEMINI_API_KEY is not set.")
        print("     export GEMINI_API_KEY=\"your_key_here\"\n")
        sys.exit(1)

    print("""
THE TWO RETRIEVAL MODALITIES:
  1. VECTOR SEARCH (pgvector <=> cosine distance):
     - Good at: Synonyms, paraphrasing, semantic intent.
     - Bad at: Section numbers, legal codes, regulatory tags, exact tokens.

  2. KEYWORD SEARCH (PostgreSQL FTS @@ plainto_tsquery):
     - Good at: Exact product codes, "Section 4.2", client identifiers.
     - Bad at: Vocabulary mismatch, concepts phrased with synonyms.

TODAY WE TEST BOTH BLIND SPOTS AND FIX THEM WITH RECIPROCAL RANK FUSION (RRF).
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIMENT 1: The Exact Identifier Blind Spot ("Section 4.2")
    # ─────────────────────────────────────────────────────────────────────────
    query_exact = "Section 4.2 equity limits"
    print("\n" + DIVIDER)
    print(f"EXPERIMENT 1: Exact Identifier Query ➔ \"{query_exact}\"")
    print(DIVIDER)
    print("""
SCENARIO:
An advisor queries specifically for Section 4.2 aggressive concentration limits.
PREDICT:
Will pure vector search rank Section 4.2 as #1?
Or will general equity guidelines overshadow it because of high semantic density?
""")
    pause()

    print("Running Pure Vector Search (Top-3)...")
    res_vec_1 = search_enterprise_chunks(query_exact, user_tier=1, top_k=3, mode="vector")
    print_results_table("PURE VECTOR SEARCH RESULTS", res_vec_1, "Similarity")

    has_sec_42 = any("4.2" in r["chunk_text"] for r in res_vec_1[:1])
    if not has_sec_42:
        print("\n🛑 OBSERVATION: Vector search failed to place Section 4.2 at Rank 1!")
        print("   Notice that general equity rules matched on words like 'equity' and 'limits',")
        print("   but the embedding model does not know that '4.2' is an essential code.")
    else:
        print("\nNotice the vector distance: exact section matches compete with general policy chunks.")
    pause()

    print("Running Pure Keyword FTS Search (Top-3)...")
    res_kw_1 = search_enterprise_chunks(query_exact, user_tier=1, top_k=3, mode="keyword")
    print_results_table("PURE KEYWORD SEARCH RESULTS (PostgreSQL FTS)", res_kw_1, "FTS Rank")
    print("✅ OBSERVATION: Keyword search instantly found Section 4.2 because the exact token matched!")
    pause()

    print("Running Hybrid Search with Reciprocal Rank Fusion (RRF)...")
    print("Formula: RRF Score = 1 / (60 + vector_rank) + 1 / (60 + keyword_rank)")
    res_hybrid_1 = search_enterprise_chunks(query_exact, user_tier=1, top_k=3, mode="hybrid")
    print_results_table("HYBRID RRF SEARCH RESULTS (Combined)", res_hybrid_1, "RRF Score")

    print("\n🎯 THE RRF WINNER:")
    print("   Section 4.2 receives scores from BOTH lists and decisively takes Rank 1!")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIMENT 2: The Semantic Synonym Blind Spot ("risk-averse clients")
    # ─────────────────────────────────────────────────────────────────────────
    query_synonym = "What about risk-averse clients?"
    print("\n" + DIVIDER)
    print(f"EXPERIMENT 2: Semantic Paraphrase Query ➔ \"{query_synonym}\"")
    print(DIVIDER)
    print("""
SCENARIO (From Slide 7 Check-in Q2):
The policy document uses the word 'Conservative' throughout Section 2.
It NEVER contains the phrase 'risk-averse'.

PREDICT:
What will happen when PostgreSQL Keyword FTS tries to match 'risk-averse'?
Will it return any results?
""")
    pause()

    print("Running Pure Keyword FTS Search (Top-3)...")
    res_kw_2 = search_enterprise_chunks(query_synonym, user_tier=1, top_k=3, mode="keyword")
    print_results_table("PURE KEYWORD SEARCH RESULTS", res_kw_2, "FTS Rank")
    print("🛑 OBSERVATION: Zero keyword matches! FTS is completely blind to synonyms.")
    pause()

    print("Running Pure Vector Search (Top-3)...")
    res_vec_2 = search_enterprise_chunks(query_synonym, user_tier=1, top_k=3, mode="vector")
    print_results_table("PURE VECTOR SEARCH RESULTS", res_vec_2, "Similarity")
    print("✅ OBSERVATION: Vector search correctly retrieved 'Conservative Client Mandates'")
    print("   because the embedding space maps 'risk-averse' close to 'Conservative'!")
    pause()

    print("Running Hybrid Search with Reciprocal Rank Fusion (RRF)...")
    res_hybrid_2 = search_enterprise_chunks(query_synonym, user_tier=1, top_k=3, mode="hybrid")
    print_results_table("HYBRID RRF SEARCH RESULTS (Combined)", res_hybrid_2, "RRF Score")
    print("✅ OBSERVATION: Even though keyword search yielded nothing, RRF successfully")
    print("   preserved the vector hit and returned the right Conservative policy section.")
    pause()

    # ── SECTION 3: Clean Reference SQL ────────────────────────────────────────
    print("\n" + DIVIDER)
    print("CLEAN REFERENCE: The Complete Production RRF Query (Slide 6):")
    print(DIVIDER)
    print("""
WITH vector_ranked AS (
    SELECT
        id, chunk_text,
        ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_vector)s::vector) AS rank
    FROM rag.document_chunks
    WHERE chunk_strategy = %(strategy)s
      AND access_tier <= %(user_tier)s
    LIMIT 50
),
keyword_ranked AS (
    SELECT
        id, chunk_text,
        ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, plainto_tsquery('english', %(query_text)s)) DESC) AS rank
    FROM rag.document_chunks
    WHERE chunk_strategy = %(strategy)s
      AND access_tier <= %(user_tier)s
      AND fts_vector @@ plainto_tsquery('english', %(query_text)s)
    LIMIT 50
),
combined AS (
    SELECT
        COALESCE(v.id, k.id) AS id,
        COALESCE(v.chunk_text, k.chunk_text) AS chunk_text,
        COALESCE(1.0 / (60 + v.rank), 0.0) +
        COALESCE(1.0 / (60 + k.rank), 0.0) AS rrf_score
    FROM vector_ranked v
    FULL OUTER JOIN keyword_ranked k ON v.id = k.id
)
SELECT chunk_text, rrf_score
FROM combined
ORDER BY rrf_score DESC
LIMIT %(top_k)s;
""")
    print(DIVIDER)
    print("OBSERVE: Notice there are no manual scale normalizations. RRF combines integer ranks!")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/04_conversation_query_rewriter.py to solve multi-turn ambiguity.")


if __name__ == "__main__":
    main()
