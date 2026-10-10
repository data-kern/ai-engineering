#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 05: Multi-Tenant Access Control & Security-Scoped Retrieval

What you will learn:
  1. The Authorization Gap: Why multi-tenant enterprise RAG cannot use global vector indexes
  2. The Danger of Post-Retrieval Filtering: Information leakage and adversarial boundary probing
  3. Database-Level Predicate Scoping: Enforcing 'WHERE access_tier <= user_tier' directly in SQL
  4. Simulating Junior Advisor (Tier 1), Senior Advisor (Tier 3), and Compliance Officer (Tier 4)

Usage:
  python scripts/05_access_control_filter.py
"""

import os
import sys

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.step3_hybrid_search import search_enterprise_chunks, get_db_connection
from app.step5_generate import call_llm
from app.step4_inject_secure import build_secure_rag_prompt

DIVIDER = "═" * 74
SUB_DIVIDER = "─" * 74


def pause():
    try:
        input("\n🔍 Press ENTER to continue ➔ ")
    except (EOFError, KeyboardInterrupt):
        pass
    print("\n" + SUB_DIVIDER)


def main():
    print("\n" + DIVIDER)
    print("  DATAKERN SESSION 5: SCRIPT 05 — ACCESS-SCOPED RETRIEVAL")
    print(DIVIDER)

    # Validate prerequisite API key
    provider = os.getenv("EMBEDDING_PROVIDER", "jina").lower().strip()
    if provider == "jina" and not os.getenv("JINA_API_KEY"):
        print("❌ MISSING PREREQUISITE: JINA_API_KEY is not set.")
        print("   Embedding the query vector requires an active Jina key:")
        print("     export JINA_API_KEY=\"your_key_here\"\n")
        sys.exit(1)
    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("❌ MISSING PREREQUISITE: GEMINI_API_KEY is not set.")
        print("     export GEMINI_API_KEY=\"your_key_here\"\n")
        sys.exit(1)

    print("""
THE ENTERPRISE HIERARCHY (Slide 11):
  ┌────────────────────────────────────────────────────────────────────────┐
  │  TIER 1: Junior Advisor                                                │
  │  → Permitted: Public Investment Policy, General Risk Guidelines        │
  │                                                                        │
  │  TIER 3: Senior Advisor                                                │
  │  → Permitted: All Tier 1 + Confidential Client Profiles & Trusts       │
  │                                                                        │
  │  TIER 4: Compliance Officer                                            │
  │  → Permitted: All Tiers + Internal Forensic Audits & Trade Freezes     │
  └────────────────────────────────────────────────────────────────────────┘

THE DANGER:
In Session 4, all queries searched all rows of rag.document_chunks.
A Junior Advisor asking about unapproved trades would retrieve confidential
forensic audit memos regarding penalized colleagues. That is a regulatory violation.
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # THE SENSITIVE COMPLIANCE QUERY
    # ─────────────────────────────────────────────────────────────────────────
    sensitive_query = "What forensic audit findings exist regarding unapproved aggressive stock concentration breaches?"

    print(f"SENSITIVE QUERY: \"{sensitive_query}\"\n")

    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATION 1: Junior Advisor (Tier 1) Attempts Retrieval
    # ─────────────────────────────────────────────────────────────────────────
    print("SIMULATION 1: User is Alex Mercer (Junior Advisor, Access Tier 1)")
    print("""
PREDICT:
With database-level predicate 'WHERE access_tier <= 1':
Will the database return the CCO Forensic Audit Memo (Tier 4)?
""")
    pause()

    results_tier1 = search_enterprise_chunks(
        query_text=sensitive_query,
        user_tier=1,
        top_k=3,
        mode="hybrid"
    )

    print(f"Results returned to Junior Advisor (Tier 1): {len(results_tier1)} chunks found.")
    for i, r in enumerate(results_tier1):
        print(f"  Chunk #{i+1} | Document: {r['doc_title']} | Tier: {r['access_tier']}")
        print(f"    Snippet: {r['chunk_text'][:120].strip()}...\n")

    has_audit_memo = any("COMP-2026" in r["chunk_text"] or r["access_tier"] == 4 for r in results_tier1)
    if not has_audit_memo:
        print("🛡️  SECURITY ENFORCED: Zero confidential audit memos leaked!")
        print("   The Junior Advisor only sees public Section 4.2 guidelines.")
    else:
        print("🚨 LEAK DETECTED!")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATION 2: Senior Advisor (Tier 3) Attempts Retrieval
    # ─────────────────────────────────────────────────────────────────────────
    print("SIMULATION 2: User is Sarah Sterling (Senior Advisor, Access Tier 3)")
    print("""
PREDICT:
Can Sarah access Harold Peterson's confidential pension records (Tier 3)?
Can she access the internal CCO disciplinary memo (Tier 4)?
""")
    pause()

    results_tier3 = search_enterprise_chunks(
        query_text=sensitive_query,
        user_tier=3,
        top_k=3,
        mode="hybrid"
    )

    print(f"Results returned to Senior Advisor (Tier 3): {len(results_tier3)} chunks found.")
    for i, r in enumerate(results_tier3):
        print(f"  Chunk #{i+1} | Document: {r['doc_title']} | Tier: {r['access_tier']}")
    print("🛡️  Tier 4 audit memo remains locked down and completely inaccessible.")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATION 3: Compliance Officer (Tier 4) Runs Retrieval
    # ─────────────────────────────────────────────────────────────────────────
    print("SIMULATION 3: User is Marcus Vance (Chief Compliance Officer, Tier 4)")
    print("""
PREDICT:
With 'WHERE access_tier <= 4':
Will the full forensic memo COMP-2026-Q1-088 be unlocked?
""")
    pause()

    results_tier4 = search_enterprise_chunks(
        query_text=sensitive_query,
        user_tier=4,
        top_k=3,
        mode="hybrid"
    )

    print(f"Results returned to Compliance Officer (Tier 4): {len(results_tier4)} chunks found.")
    for i, r in enumerate(results_tier4):
        print(f"  Chunk #{i+1} | Document: {r['doc_title']} | Tier: {r['access_tier']}")
        if r["access_tier"] == 4:
            print(f"  📜 UNLOCKED MEMO EXCERPT:\n{r['chunk_text'][:250]}...\n")

    print("✅ Full audit documentation unlocked for authorized compliance officer.")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # ARCHITECTURAL CRITICAL THINKING (Slide 18, Q3)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + DIVIDER)
    print("ENGINEERING QUESTION: Pre-Filter (SQL) vs Post-Filter (Python/LLM)")
    print(DIVIDER)
    print("""
Why is filtering in SQL superior to filtering AFTER retrieval?

1. THE POST-FILTER RISK:
   If Python retrieves Tier 4 chunks into memory and attempts to hide them
   from the user via an 'if user.tier >= chunk.tier' check:
   - The memory buffer already contains confidential data.
   - If chunks are passed to the LLM with a prompt instruction 'do not mention confidential data',
     jailbreaking and prompt injection attacks can easily trick the LLM into leaking it.
   - Information leakage via timing attacks or token counts.

2. THE SQL DATABASE PREDICATE (THE RIGHT WAY):
   - 'WHERE access_tier <= user_tier' executes BEFORE index traversal.
   - The database engine never evaluates, scores, or returns restricted rows.
   - Zero possibility of leakage to the application or LLM layer.
""")
    pause()

    # ── SECTION 4: Clean Reference SQL ────────────────────────────────────────
    print("\n" + DIVIDER)
    print("CLEAN REFERENCE: Access-Scoped Retrieval SQL (Slide 12):")
    print(DIVIDER)
    print("""
SELECT chunk_text, doc_title, access_tier
FROM rag.document_chunks
WHERE chunk_strategy = %(strategy)s
  AND access_tier <= %(user_tier)s     -- ← DATABASE-LEVEL SECURITY PREDICATE
ORDER BY embedding <=> %(query_vector)s::vector
LIMIT %(top_k)s;
""")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/06_prompt_injection_defense.py to defend against adversarial documents.")


if __name__ == "__main__":
    main()
