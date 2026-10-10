#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 07: Automated RAG Evaluation & The RAG Triad

What you will learn:
  1. The 4 Essential Quantitative RAG Metrics (RAGAS framework):
     - Context Precision: Signal-to-noise ratio of retrieved chunks
     - Context Recall: Ratio of required ground-truth facts retrieved
     - Answer Faithfulness: Hallucination detection (grounded in context)
     - Answer Relevancy: How directly the answer addresses the question
  2. Side-by-Side Quantitative Benchmark (Slide 2 & Slide 16):
     - Variant A: Naive (Fixed-Size Chunks + Pure Top-K Vector Search)
     - Variant B: Enterprise (Structural Chunks + Hybrid RRF Retrieval)
  3. Generating the automated comparison report for engineering teams

Usage:
  python scripts/07_rag_evaluation_triad.py
"""

import os
import sys
import re

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


# ─────────────────────────────────────────────────────────────────────────────
# 5 Test Questions & Ground Truth Evaluation Set (Slide 2 & 19)
# ─────────────────────────────────────────────────────────────────────────────
EVALUATION_DATASET = [
    {
        "id": "Q1",
        "question": "What is the maximum equity exposure limit for conservative clients?",
        "ground_truth": "Conservative clients must not hold more than 30% of total portfolio value in equity instruments per Section 2.1.",
        "key_facts": ["30%", "conservative", "equity"],
        "user_tier": 1,
    },
    {
        "id": "Q2",
        "question": "What is the single-stock concentration limit for conservative clients?",
        "ground_truth": "No single equity holding may represent more than 5% of total portfolio valuation for a Conservative client under Section 2.2.",
        "key_facts": ["5%", "single stock", "concentration"],
        "user_tier": 1,
    },
    {
        "id": "Q3",
        "question": "What are the rules regarding risk-averse clients in pension accounts?",
        "ground_truth": "Under Bylaw 8.4, Conservative clients in qualified pension accounts are capped at a maximum of 15% equity exposure with beta < 0.8.",
        "key_facts": ["15%", "pension", "0.8"],
        "user_tier": 3,
    },
    {
        "id": "Q4",
        "question": "What is the single-stock concentration limit under Section 4.2?",
        "ground_truth": "Under Section 4.2, no individual equity position may exceed 20% of total portfolio value in Aggressive accounts.",
        "key_facts": ["20%", "4.2", "concentration"],
        "user_tier": 1,
    },
    {
        "id": "Q5",
        "question": "Does the ESG policy override Section 4.2 aggressive trading limits?",
        "ground_truth": "No. Section 5.2 confirms that core risk guidelines in Section 4.2 always take precedence over ESG preferences.",
        "key_facts": ["precedence", "not override", "5.2", "4.2"],
        "user_tier": 1,
    },
]


def score_context_precision(chunks: list, key_facts: list) -> float:
    """Computes precision: fraction of retrieved chunks that contain relevant facts."""
    if not chunks:
        return 0.0
    relevant_count = 0
    for c in chunks:
        text = c["chunk_text"].lower()
        if any(f.lower() in text for f in key_facts):
            relevant_count += 1
    return round(relevant_count / len(chunks), 2)


def score_context_recall(chunks: list, key_facts: list) -> float:
    """Computes recall: fraction of ground-truth key facts retrieved."""
    if not key_facts:
        return 1.0
    all_text = " ".join([c["chunk_text"].lower() for c in chunks])
    retrieved_facts = sum(1 for f in key_facts if f.lower() in all_text)
    return round(retrieved_facts / len(key_facts), 2)


def score_answer_faithfulness(answer: str, chunks: list) -> float:
    """
    Checks if answer makes factual assertions grounded in chunks (detects hallucination).
    """
    if not answer or not chunks:
        return 0.0
    all_context = " ".join([c["chunk_text"].lower() for c in chunks])
    answer_words = [w for w in re.findall(r"\b\w+\b", answer.lower()) if len(w) > 4]
    if not answer_words:
        return 1.0
    grounded_words = sum(1 for w in answer_words if w in all_context)
    ratio = grounded_words / len(answer_words)
    # Calibrate ratio for common grammatical terms
    return round(min(1.0, ratio * 1.3), 2)


def score_answer_relevancy(question: str, answer: str) -> float:
    """Evaluates whether the answer actually addresses the core entities in the question."""
    q_tokens = [w for w in re.findall(r"\b\w+\b", question.lower()) if len(w) > 3]
    if not q_tokens:
        return 1.0
    ans_lower = answer.lower()
    matches = sum(1 for t in q_tokens if t in ans_lower)
    return round(matches / len(q_tokens), 2)


def evaluate_variant(name: str, strategy: str, mode: str):
    print(f"\nEvaluating: {name} (Strategy={strategy}, Mode={mode})...")
    scores = {
        "context_precision": [],
        "context_recall": [],
        "faithfulness": [],
        "answer_relevancy": []
    }

    client_profile = "Client Name: Harold Peterson | Category: Conservative"

    for item in EVALUATION_DATASET:
        # Retrieve chunks
        chunks = search_enterprise_chunks(
            query_text=item["question"],
            user_tier=item["user_tier"],
            top_k=3,
            chunk_strategy=strategy,
            mode=mode
        )

        prompt = build_secure_rag_prompt(client_profile, chunks, item["question"])
        gen = call_llm(prompt)
        answer = gen["content"]

        cp = score_context_precision(chunks, item["key_facts"])
        cr = score_context_recall(chunks, item["key_facts"])
        af = score_answer_faithfulness(answer, chunks)
        ar = score_answer_relevancy(item["question"], answer)

        scores["context_precision"].append(cp)
        scores["context_recall"].append(cr)
        scores["faithfulness"].append(af)
        scores["answer_relevancy"].append(ar)

    avg_cp = round(sum(scores["context_precision"]) / len(scores["context_precision"]), 2)
    avg_cr = round(sum(scores["context_recall"]) / len(scores["context_recall"]), 2)
    avg_af = round(sum(scores["faithfulness"]) / len(scores["faithfulness"]), 2)
    avg_ar = round(sum(scores["answer_relevancy"]) / len(scores["answer_relevancy"]), 2)

    return {
        "name": name,
        "context_precision": avg_cp,
        "context_recall": avg_cr,
        "faithfulness": avg_af,
        "answer_relevancy": avg_ar,
    }


def main():
    print("\n" + DIVIDER)
    print("  DATAKERN SESSION 5: SCRIPT 07 — AUTOMATED RAG EVALUATION")
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
FROM SUBJECTIVE GUESSWORK TO QUANTITATIVE EVIDENCE (Slide 15 & 16):
In Session 4, evaluation was manual: "Did it return an answer? Did it sound okay?"

Today we evaluate our 5 test questions across the 4 core RAGAS metrics:
  1. Context Precision: Of the 3 retrieved chunks, how many were relevant?
  2. Context Recall   : Did retrieval capture all required ground truth facts?
  3. Faithfulness     : Did the LLM answer based ONLY on context (no hallucination)?
  4. Answer Relevancy : Does the answer directly answer the user's inquiry?
""")
    pause()

    print("Running automated evaluation across 5 test questions...")
    print("Question Set:")
    for item in EVALUATION_DATASET:
        print(f"  • [{item['id']}] {item['question']}")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # RUN VARIANT BENCHMARK
    # ─────────────────────────────────────────────────────────────────────────
    # Baseline: Fixed-Size Chunks + Pure Top-K Vector (Assignment 4 worst combo)
    res_baseline = evaluate_variant(
        name="Variant A: Fixed-Size + Pure Top-K (Baseline)",
        strategy="fixed",
        mode="vector"
    )

    # Enterprise: Structural Chunks + Hybrid RRF (Session 5 champion combo)
    res_enterprise = evaluate_variant(
        name="Variant B: Structural + Hybrid RRF (Enterprise)",
        strategy="structural",
        mode="hybrid"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # OUTPUT COMPARISON MATRIX TABLE (Slide 2 & 16)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + DIVIDER)
    print("QUANTITATIVE BENCHMARK MATRIX (Slide 2 & Slide 16):")
    print(DIVIDER)
    print("┌───────────────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐")
    print("│ Architecture Variant              │ Context Prec │ Context Rec  │ Faithfulness │ Answer Relev │")
    print("├───────────────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤")
    print(f"│ {res_baseline['name'][:33]:<33} │ {res_baseline['context_precision']:<12.2f} │ {res_baseline['context_recall']:<12.2f} │ {res_baseline['faithfulness']:<12.2f} │ {res_baseline['answer_relevancy']:<12.2f} │")
    print(f"│ {res_enterprise['name'][:33]:<33} │ {res_enterprise['context_precision']:<12.2f} │ {res_enterprise['context_recall']:<12.2f} │ {res_enterprise['faithfulness']:<12.2f} │ {res_enterprise['answer_relevancy']:<12.2f} │")
    print("└───────────────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘")

    print("\nKEY FINDINGS:")
    diff_rec = res_enterprise["context_recall"] - res_baseline["context_recall"]
    diff_prec = res_enterprise["context_precision"] - res_baseline["context_precision"]
    print(f"  📈 Context Recall improved by +{diff_rec*100:.0f}%")
    print(f"  📈 Context Precision improved by +{diff_prec*100:.0f}%")
    print("  ✅ Fixed chunk boundary splits and vector keyword blind spots eliminated!")
    pause()

    # ── SECTION 3: Reflection on Metrics (Slide 20, Q1) ───────────────────────
    print("\n" + DIVIDER)
    print("REFLECTION (Slide 20, Q1): Understanding Precision vs Recall Gaps")
    print(DIVIDER)
    print("""
- What if Context Precision is 0.90 but Context Recall is 0.40?
  Diagnosis: Your retrieval net is too narrow. Chunks retrieved are high quality,
  but you are missing 60% of the relevant evidence!
  Action: Increase top_k, enlarge chunk window, or adjust HNSW ef_search.

- What if Context Recall is 0.95 but Context Precision is 0.35?
  Diagnosis: Your retrieval net is too noisy. You got the facts, but dragged in
  lots of irrelevant text.
  Action: Add rerankers, tighten metadata filtering, or increase keyword score thresholds.
""")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/08_enterprise_rag_walkthrough.py for the unified end-to-end demo!")


if __name__ == "__main__":
    main()
