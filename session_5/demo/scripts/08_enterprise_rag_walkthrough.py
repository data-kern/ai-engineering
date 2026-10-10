#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 08: Unified Enterprise RAG Architecture Walkthrough

What you will learn:
  1. The complete end-to-end Enterprise RAG flow (Slide 17):
     User Message + History ➔ Sanitizer ➔ Query Rewriter ➔ Security Hybrid RRF ➔ Secure Prompt ➔ LLM
  2. Live observation of latency breakdown across all 5 stages
  3. Real-world scenario testing: Multi-turn, Exact code matching, Access control, and Injection defense
  4. The architectural bridge from Enterprise RAG to Session 6 (AI Agents)

Usage:
  python scripts/08_enterprise_rag_walkthrough.py
"""

import os
import sys

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.schema import EnterpriseRAGRequest, ChatMessage, UserContext
from app.enterprise_pipeline import run_enterprise_rag

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
    print("  DATAKERN SESSION 5: SCRIPT 08 — ENTERPRISE RAG FULL WALKTHROUGH")
    print(DIVIDER)

    # Validate prerequisite API keys
    missing = []
    if not os.getenv("JINA_API_KEY") and os.getenv("EMBEDDING_PROVIDER", "jina").lower().strip() == "jina":
        missing.append("export JINA_API_KEY=\"your_jina_key\"")
    if not os.getenv("GROQ_API_KEY"):
        missing.append("export GROQ_API_KEY=\"your_groq_key\"")
    if missing:
        print("❌ MISSING PREREQUISITES:")
        for m in missing:
            print(f"   {m}")
        print("\nPlease export the required environment variables and re-run.\n")
        sys.exit(1)

    print("""
THE COMPLETE ENTERPRISE RAG ARCHITECTURE (Slide 17):

  ┌──────────────┐
  │ User Query   │
  │ + History    │
  └──────┬───────┘
         │
         ▼
  [STAGE 1: INPUT SANITIZER]      ➔ Scans for prompt injection triggers
         │
         ▼
  [STAGE 2: QUERY REWRITER]       ➔ Condenses dialogue into standalone query
         │ (Standalone Query)
         ▼
  [STAGE 3: HYBRID RRF RETRIEVAL] ➔ WHERE access_tier <= user_tier
         │ (Top Chunks)             Vector (pgvector) + Keyword (FTS) combined via RRF
         ▼
  [STAGE 4: SECURE PROMPT]        ➔ Wraps in [START_DOCUMENT]...[END_DOCUMENT]
         │ (Augmented Prompt)
         ▼
  [STAGE 5: GROQ LLM GENERATION]  ➔ Compliant, grounded, policy-enforced output
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO: Senior Advisor Managing Harold Peterson
    # ─────────────────────────────────────────────────────────────────────────
    senior_advisor = UserContext(
        user_id="adv-804",
        name="Sarah Sterling",
        role="Senior Wealth Partner",
        access_tier=3  # Has Tier 3 clearance (can see client pension rules)
    )

    print("AUTHENTICATED USER CONTEXT:")
    print(f"  User Name   : {senior_advisor.name}")
    print(f"  Role        : {senior_advisor.role}")
    print(f"  Access Tier : Tier {senior_advisor.access_tier} (Public + Confidential Client Records)")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # TURN 1: The Initial Policy Inquiry
    # ─────────────────────────────────────────────────────────────────────────
    turn_1_message = "What is the equity limit for conservative clients?"
    print("\n" + DIVIDER)
    print(f"TURN 1: \"{turn_1_message}\"")
    print(DIVIDER)

    req1 = EnterpriseRAGRequest(
        message=turn_1_message,
        conversation_history=[],
        user_context=senior_advisor,
        use_hybrid=True,
        top_k=3
    )

    resp1 = run_enterprise_rag(req1)

    print("\nSTAGE 1 & 2: Rewriting was skipped (first turn; message already standalone).")
    print(f"STAGE 3: Retrieved {len(resp1.retrieved_chunks)} chunks using Hybrid RRF.")
    print("STAGE 4: Structural enclosures applied.")
    print("\nAI RESPONSE (Turn 1):")
    print(f"  \"{resp1.answer}\"")

    print("\n⏱️  LATENCY BREAKDOWN:")
    for stage, ms in resp1.latency_breakdown_ms.items():
        print(f"   • {stage:<22}: {ms:>6.2f} ms")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # TURN 2: The Ambiguous Follow-Up (Context Condensation Test)
    # ─────────────────────────────────────────────────────────────────────────
    turn_2_message = "What about pension accounts specifically?"
    print("\n" + DIVIDER)
    print(f"TURN 2: \"{turn_2_message}\" (Ambiguous Follow-Up)")
    print(DIVIDER)
    print("""
PREDICT:
Watch Stage 2 transform this 5-word sentence into a standalone search query.
Then watch Stage 3 use Sarah's Tier 3 authorization to retrieve the 15% Pension Rule!
""")
    pause()

    history = [
        ChatMessage(role="user", content=turn_1_message),
        ChatMessage(role="assistant", content=resp1.answer),
    ]

    req2 = EnterpriseRAGRequest(
        message=turn_2_message,
        conversation_history=history,
        user_context=senior_advisor,
        use_hybrid=True,
        top_k=3
    )

    resp2 = run_enterprise_rag(req2)

    print(f"\n✅ STAGE 2 QUERY REWRITING TRIGGERED:")
    print(f"   Original Follow-Up : \"{turn_2_message}\"")
    print(f"   Rewritten Query    : \"{resp2.rewritten_query}\"")

    print(f"\n✅ STAGE 3 HYBRID RRF RETRIEVAL:")
    for i, c in enumerate(resp2.retrieved_chunks):
        print(f"   #{i+1} [RRF: {c.rrf_score:.4f}] Tier {c.access_tier} | {c.doc_title}")
        print(f"       Snippet: {c.chunk_text[:120].strip()}...")

    print("\nAI RESPONSE (Turn 2):")
    print(f"  \"{resp2.answer}\"")

    print("\n⏱️  LATENCY BREAKDOWN:")
    for stage, ms in resp2.latency_breakdown_ms.items():
        print(f"   • {stage:<22}: {ms:>6.2f} ms")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # TURN 3: Testing Authorization Boundaries (Access Control Test)
    # ─────────────────────────────────────────────────────────────────────────
    turn_3_message = "Show me the confidential CCO forensic audit memo on unapproved stock breaches."
    print("\n" + DIVIDER)
    print(f"TURN 3: SECURITY PROBE ➔ \"{turn_3_message}\"")
    print(DIVIDER)
    print("""
SCENARIO:
Sarah is a Senior Advisor (Tier 3). She asks for Tier 4 internal audit records.
PREDICT:
Will the database let Sarah see the CCO Forensic Audit memo?
""")
    pause()

    req3 = EnterpriseRAGRequest(
        message=turn_3_message,
        conversation_history=[],
        user_context=senior_advisor,  # Tier 3
        use_hybrid=True,
        top_k=3
    )

    resp3 = run_enterprise_rag(req3)

    leaked = any(c.access_tier == 4 for c in resp3.retrieved_chunks)
    if not leaked:
        print("🛡️  ACCESS CONTROL VERIFIED:")
        print("   Database SQL predicate 'WHERE access_tier <= 3' strictly prevented")
        print("   retrieving Tier 4 compliance audit documents!")
        print(f"\nAI Response: \"{resp3.answer}\"")
    else:
        print("🚨 CRITICAL ERROR: Access control leak!")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # CONCLUSION & BRIDGE TO SESSION 6 (Slide 21 & 22)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + DIVIDER)
    print("SESSION 5 WRAP-UP: THE ROAD TO PRODUCTION AI")
    print(DIVIDER)
    print("""
REVIEW OF TODAY'S 5 UPGRADES:
  ✅ 1. Hybrid Search (RRF)    : Vector meaning + Keyword exact codes combined.
  ✅ 2. Query Rewriter         : Ambiguous dialogues condensed into standalone queries.
  ✅ 3. Access Control         : Multi-tier security enforced directly at the SQL layer.
  ✅ 4. Prompt Injection       : Untrusted documents neutralized with structural boundaries.
  ✅ 5. Quantitative Eval      : Groundedness, Precision, and Recall measured with numbers.

"Session 4 gave the AI a memory. Session 5 made that memory trustworthy."
— Uma Kiran | DataKern

WHAT'S NEXT IN SESSION 6: AI AGENTS
Right now, our pipeline is static: Rewrite ➔ Retrieve ➔ Generate.
In Session 6, we give the LLM TOOLS (SQL queries, live stock APIs, escalation endpoints)
and let the AI DECIDE what to do and when to act!
""")
    print(DIVIDER)
    print("Demo complete! You can start the live HTTP service with:")
    print("  uvicorn app.main:app --port 8000 --reload")


if __name__ == "__main__":
    main()
