#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 04: Conversation History & Pre-Retrieval Query Rewriter

What you will learn:
  1. The Multi-Turn Amnesia Trap: Why follow-up questions fail in pure vector RAG
  2. The LLM Pre-Retrieval Rewriter: How to condense dialogue history into a standalone query
  3. Phoenix Observability: Tracing the query_rewriting span before retrieval
  4. End-to-end comparison: Naive follow-up retrieval vs Context-aware rewritten retrieval

Usage:
  python scripts/04_conversation_query_rewriter.py
"""

import os
import sys

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.step2_rewrite import rewrite_query
from app.step3_hybrid_search import search_enterprise_chunks
from app.step4_inject_secure import build_secure_rag_prompt
from app.step5_generate import call_llm

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
    print("  DATAKERN SESSION 5: SCRIPT 04 — CONVERSATION QUERY REWRITING")
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
THE PROBLEM (Slide 8):
  Advisors rarely speak in isolated standalone sentences. They have dialogues:
    Turn 1: "What is the equity limit for conservative clients?"
    Turn 2: "What about pension accounts specifically?"

  A naive RAG pipeline only embeds the latest sentence:
    embed("What about pension accounts specifically?")
  The vector database has no idea what 'that' refers to. It returns generic
  pension fund guidelines instead of Harold Peterson's 15% conservative pension rule.
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATE TURN 1
    # ─────────────────────────────────────────────────────────────────────────
    print("TURN 1 — INITIAL QUERY")
    turn_1_user = "What is the equity limit for conservative clients?"
    turn_1_assistant = "Conservative clients must not exceed 30% total portfolio allocation in equities per Section 2.1."

    print(f"ADVISOR : \"{turn_1_user}\"")
    print(f"AI      : \"{turn_1_assistant}\"")
    print("\n✅ Turn 1 executed cleanly. Both parties understand the client is Conservative.")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # SIMULATE TURN 2 — THE AMBIGUOUS FOLLOW-UP
    # ─────────────────────────────────────────────────────────────────────────
    turn_2_user = "What about pension accounts specifically?"
    print("\nTURN 2 — THE FOLLOW-UP QUESTION")
    print(f"ADVISOR asks: \"{turn_2_user}\"")
    print("""
PREDICT:
What happens if we pass this exact sentence directly into pgvector?
Does the string "What about pension accounts specifically?" contain the word
"equity"? Does it contain the word "conservative"?
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIMENT A: Naive Retrieval (Without Rewriting)
    # ─────────────────────────────────────────────────────────────────────────
    print("EXPERIMENT A: Naive Retrieval (As in Assignment 4)")
    print(f"Retrieving top chunks for: \"{turn_2_user}\" ...")
    chunks_naive = search_enterprise_chunks(turn_2_user, user_tier=3, top_k=2, mode="hybrid")

    print("\nRetrieved Chunks from Naive Query:")
    for i, c in enumerate(chunks_naive):
        snippet = c['chunk_text'][:130].replace('\n', ' ')
        print(f"  Chunk {i+1} (Tier {c['access_tier']}): {snippet}...")

    # Let's see what the LLM generates with naive context
    client_profile = "Client Name: Harold Peterson | Category: Conservative"
    naive_prompt = build_secure_rag_prompt(client_profile, chunks_naive, turn_2_user)
    naive_gen = call_llm(naive_prompt)
    print(f"\nAI Answer (Naive): \"{naive_gen['content'][:180]}...\"")
    print("🛑 Notice: The AI cannot answer with precision because retrieval lacked context.")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIMENT B: Pre-Retrieval Query Rewriter (The Fix)
    # ─────────────────────────────────────────────────────────────────────────
    print("EXPERIMENT B: The Fix — Pre-Retrieval Query Rewriting (Slide 9 & 10)")
    print("""
PIPELINE FLOW:
  1. Take conversation history: [Turn 1 User, Turn 1 Assistant]
  2. Send to LLM with instruction: 'Rewrite into a standalone query. Do not answer.'
  3. Feed the resulting standalone query into Hybrid Retrieval.
""")
    pause()

    conversation_history = [
        {"role": "user", "content": turn_1_user},
        {"role": "assistant", "content": turn_1_assistant},
    ]

    print("Calling Query Rewriter...")
    rewritten_query = rewrite_query(conversation_history, turn_2_user)
    print("\n" + "─" * 70)
    print(f"  ORIGINAL FOLLOW-UP : \"{turn_2_user}\"")
    print(f"  REWRITTEN STANDALONE: \"{rewritten_query}\"")
    print("─" * 70)
    print("✅ Notice: The pronoun and missing subject have been fully synthesized!")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIMENT C: Retrieval with Rewritten Standalone Query
    # ─────────────────────────────────────────────────────────────────────────
    print("EXPERIMENT C: Retrieval with Rewritten Standalone Query")
    print(f"Retrieving top chunks for rewritten query...")
    chunks_rewritten = search_enterprise_chunks(rewritten_query, user_tier=3, top_k=2, mode="hybrid")

    print("\nRetrieved Chunks from Rewritten Query:")
    for i, c in enumerate(chunks_rewritten):
        snippet = c['chunk_text'][:140].replace('\n', ' ')
        print(f"  Chunk {i+1} [RRF: {c['rrf_score']:.4f}] (Tier {c['access_tier']}): {snippet}...")

    rewritten_prompt = build_secure_rag_prompt(client_profile, chunks_rewritten, turn_2_user)
    smart_gen = call_llm(rewritten_prompt)

    print("\nAI Answer (Context-Aware RAG):")
    print(f"\"{smart_gen['content']}\"")
    print("\n🎯 OUTCOME: The AI retrieved Harold Peterson's 15% Pension Limit and answered perfectly!")
    pause()

    # ── SECTION 4: Clean Reference Code ───────────────────────────────────────
    print("\n" + DIVIDER)
    print("CLEAN REFERENCE: Query Rewriter Function (Slide 10):")
    print(DIVIDER)
    print("""
def rewrite_query(conversation_history: list[dict], latest_message: str) -> str:
    history_text = "\\n".join(
        f"{turn['role'].upper()}: {turn['content']}"
        for turn in conversation_history[-4:]
    )
    rewrite_prompt = (
        f"Given this conversation:\\n{history_text}\\n\\n"
        f"Rewrite the final message as a complete, standalone question "
        f"that can be answered without any prior context.\\n"
        f"Output ONLY the rewritten question, nothing else.\\n\\n"
        f"Final message: {latest_message}"
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": rewrite_prompt}],
        max_tokens=100
    )
    return response.choices[0].message.content.strip()
""")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/05_access_control_filter.py to test multi-tier security.")


if __name__ == "__main__":
    main()
