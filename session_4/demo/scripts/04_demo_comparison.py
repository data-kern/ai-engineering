#!/usr/bin/env python3
"""
scripts/04_demo_comparison.py — Direct LLM vs RAG: Side-by-Side Comparison

This script sends the same question to both endpoints and prints the answers
side-by-side so you can see exactly what the RAG pipeline adds.

Make sure the service is running first:
    uvicorn app.main:app --reload --port 8000

Then run:
    python scripts/04_demo_comparison.py
"""

import sys
import requests

SERVICE_URL = "http://localhost:8000"

DEFAULT_QUESTIONS = [
    "Should Mr. Peterson add more NVDA to his portfolio?",
    "What is the maximum equity exposure allowed for Mr. Peterson?",
    "Can Mr. Peterson put 80% of his portfolio into tech stocks?",
]

def pause():
    input("\n🔍 Press ENTER to continue ➔ ")
    print("\n" + "─" * 70)


def ask(endpoint: str, question: str) -> dict:
    response = requests.post(
        f"{SERVICE_URL}/{endpoint}",
        json={"question": question},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def print_comparison(question: str):
    print("\n" + "=" * 80)
    print(f"  QUESTION: {question}")
    print("=" * 80)

    print("\nPREDICT: How do you think the LLM will answer this without context?")
    pause()

    # ── Direct LLM ────────────────────────────────────────────────────────────
    print("\n❌  WITHOUT RAG  (direct LLM — no policy context)")
    print("─" * 80)
    try:
        direct = ask("ask", question)
        print(direct["answer"])
        print(f"\n  [Mode: {direct['mode']}]")
        print(f"  [Policy chunks used: {direct['retrieved_count']}]")
    except Exception as e:
        print(f"  Error calling /ask: {e}")

    print("\nPREDICT: Now, what should the answer be when the Apex Financial policy is retrieved?")
    pause()

    # ── RAG ───────────────────────────────────────────────────────────────────
    print(f"\n✅  WITH RAG  (retrieved policy context injected)")
    print("─" * 80)
    try:
        rag = ask("ask/rag", question)
        print(rag["answer"])
        print(f"\n  [Mode: {rag['mode']}]")
        print(f"  [Policy chunks retrieved: {rag['retrieved_count']}]")

        if rag["chunks_used"]:
            print(f"\n  📄 Retrieved policy sections:")
            for i, chunk in enumerate(rag["chunks_used"]):
                preview = chunk[:120].replace("\n", " ")
                print(f"     [{i+1}] {preview}...")
    except Exception as e:
        print(f"  Error calling /ask/rag: {e}")

    print("\n" + "=" * 80)


def main():
    questions = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_QUESTIONS

    print("\n" + "█" * 80)
    print("  Session 4 RAG Demo — Step 4: Direct LLM vs RAG Comparison")
    print("  Service: http://localhost:8000")
    print("█" * 80)
    print("\n  CLIENT: Mr. James Peterson | Risk Category: CONSERVATIVE")
    
    for question in questions:
        print_comparison(question)
        print("OBSERVE: See how the retrieved chunks grounded the LLM's response.")
        pause()

    print("✅ Demo complete!")
    print("Don't forget to check http://localhost:6006 to see all these calls in Phoenix.")

if __name__ == "__main__":
    main()
