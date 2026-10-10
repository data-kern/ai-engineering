#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 02: Multi-Tier Document Ingestion & Dual Indexing

What you will learn:
  1. How to chunk documents structurally vs fixed-size splits
  2. How to compute vector embeddings and populate PostgreSQL tsvectors simultaneously
  3. How to tag chunks with access_tier metadata (1: Public, 3: Client Data, 4: Compliance)
  4. How pre-index scanning flags adversarial prompt injection patterns at ingestion time

Usage:
  python scripts/02_index_enterprise_docs.py
"""

import os
import sys
import re
import psycopg2
# Add parent directory so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.step1_sanitize import scan_for_injection
from app.embeddings import embed_texts

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", os.getenv("USER", "ramadugu")),
    "password": os.getenv("DB_PASS", ""),
    "port":     os.getenv("DB_PORT", "5432"),
    "dbname":   os.getenv("DB_NAME", "postgres"),
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

DOCUMENTS_CONFIG = [
    {
        "file": os.path.join(DATA_DIR, "01_public_apex_risk_policy.txt"),
        "title": "Apex Investment Risk Policy 2026",
        "tier": 1,
        "strategy": "structural",
    },
    {
        "file": os.path.join(DATA_DIR, "02_senior_client_portfolios.txt"),
        "title": "Confidential Client Records & Pension Mandates",
        "tier": 3,
        "strategy": "structural",
    },
    {
        "file": os.path.join(DATA_DIR, "03_compliance_audit_memos.txt"),
        "title": "CCO Forensic Audit Memo (COMP-2026-Q1-088)",
        "tier": 4,
        "strategy": "structural",
    },
    {
        "file": os.path.join(DATA_DIR, "04_malicious_fund_disclosure.txt"),
        "title": "ShellCorp External Prospectus & Disclosures",
        "tier": 1,
        "strategy": "structural",
    },
]

DIVIDER = "═" * 74
SUB_DIVIDER = "─" * 74


def pause():
    try:
        input("\n🔍 Press ENTER to continue ➔ ")
    except (EOFError, KeyboardInterrupt):
        pass
    print("\n" + SUB_DIVIDER)


def chunk_structurally(text: str) -> list[str]:
    """
    Splits text along section boundaries and major headers.
    Ensures policy rules (like Section 4.2 or Pension Directives) stay intact in one chunk.
    """
    raw_sections = re.split(r"(?:={10,}|\n#{1,3}\s+|\n(?=[0-9]\.[0-9]\s+[A-Z]))", text)
    chunks = []
    for sec in raw_sections:
        cleaned = sec.strip()
        if len(cleaned) > 50:  # Ignore tiny separators
            chunks.append(cleaned)
    return chunks


def chunk_fixed_size(text: str, chunk_words: int = 150, overlap_words: int = 25) -> list[str]:
    """
    Naive fixed-size word chunker for baseline comparison.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_words])
        chunks.append(chunk)
        i += chunk_words - overlap_words
    return chunks


def main():
    print("\n" + DIVIDER)
    print("  DATAKERN SESSION 5: SCRIPT 02 — ENTERPRISE DOCUMENT INGESTION")
    print(DIVIDER)
    print("""
TODAY'S INGESTION PIPELINE (Jina AI Embeddings v3):
  1. Call Jina AI API (jina-embeddings-v3, dimensions=768, task='retrieval.passage').
  2. Parse documents using structural boundaries (preserving rule coherence).
  3. Scan each chunk for Prompt Injection triggers (Defense Layer 2).
  4. Store chunks into pgvector with:
     - Vector embedding (VECTOR(768), <=> cosine distance)
     - Full-Text Search tsvector (for keyword RRF)
     - Security access_tier (1: Public, 3: Senior, 4: Compliance)
     - embedding_model ('jina-embeddings-v3')
""")
    pause()

    # ── SECTION 1: Jina AI Embedding Provider ─────────────────────────────────
    print("SECTION 1: Hosted Embedding Provider (Jina AI)")
    
    pause()

    provider = os.getenv("EMBEDDING_PROVIDER", "jina").lower().strip()
    jina_key = os.getenv("JINA_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if provider == "jina":
        if not jina_key or not jina_key.strip():
            print("\n" + "═" * 74)
            print("❌ MISSING PREREQUISITE: JINA_API_KEY environment variable is not set.")
            print("   As taught in DataKern Assignment 4, real embeddings require an active API key.")
            print("   Please export your key in your terminal before running:")
            print("     export JINA_API_KEY=\"your_jina_key_here\"")
            print("   (Get a free trial key at https://jina.ai/embeddings)")
            print("═" * 74 + "\n")
            sys.exit(1)
        print("✅ JINA_API_KEY detected. Connecting to hosted Jina AI v3 API (jina-embeddings-v3, 768-d)...")
    elif provider == "gemini":
        if not gemini_key or not gemini_key.strip():
            print("\n" + "═" * 74)
            print("❌ MISSING PREREQUISITE: GEMINI_API_KEY environment variable is not set.")
            print("   Please export your key in your terminal before running:")
            print("     export GEMINI_API_KEY=\"your_gemini_key_here\"")
            print("═" * 74 + "\n")
            sys.exit(1)
        print("✅ GEMINI_API_KEY detected. Connecting to Google Gemini API (768-d)...")

    # ── SECTION 2: Process and Index Documents ────────────────────────────────
    print("\nSECTION 2: Multi-Tier Ingestion & Injection Scanning")
    pause()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Clear previous demo ingestion
    cur.execute("DELETE FROM rag.document_chunks;")
    print("Cleared existing rows in rag.document_chunks.\n")

    total_chunks = 0
    flagged_chunks = 0

    for doc in DOCUMENTS_CONFIG:
        path = doc["file"]
        title = doc["title"]
        tier = doc["tier"]

        if not os.path.exists(path):
            print(f"⚠️  File missing: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Generate both structural and fixed chunks for our comparative evaluation
        structural_chunks = chunk_structurally(content)
        fixed_chunks = chunk_fixed_size(content)

        print(f"📄 Indexing: {os.path.basename(path)}")
        print(f"   Title       : {title}")
        print(f"   Access Tier : Tier {tier} {'(Public)' if tier==1 else '(Senior)' if tier==3 else '(Compliance)'}")
        print(f"   Structural  : {len(structural_chunks)} chunks")
        print(f"   Fixed-Size  : {len(fixed_chunks)} chunks")

        # Compute embeddings for structural chunks via Jina AI
        structural_vectors = embed_texts(structural_chunks, purpose="document")

        # Ingest structural chunks
        for idx, (chunk_text, vector) in enumerate(zip(structural_chunks, structural_vectors)):
            # Injection scan check
            is_flagged, triggers = scan_for_injection(chunk_text)
            if is_flagged:
                flagged_chunks += 1
                print(f"   🚨 [ALERT] Chunk {idx+1} flagged for Prompt Injection: {triggers}")

            cur.execute("""
                INSERT INTO rag.document_chunks (
                    doc_title, source_file, chunk_index, access_tier,
                    chunk_strategy, chunk_text, embedding_model, embedding, fts_vector
                ) VALUES (
                    %s, %s, %s, %s,
                    'structural', %s, 'jina-embeddings-v3', %s, to_tsvector('english', %s)
                );
            """, (title, path, idx, tier, chunk_text, vector, chunk_text))
            total_chunks += 1

        # Compute embeddings for fixed-size chunks via Jina AI
        fixed_vectors = embed_texts(fixed_chunks, purpose="document")

        # Also store fixed-size chunks under chunk_strategy='fixed' for baseline testing
        for idx, (chunk_text, vector) in enumerate(zip(fixed_chunks, fixed_vectors)):
            cur.execute("""
                INSERT INTO rag.document_chunks (
                    doc_title, source_file, chunk_index, access_tier,
                    chunk_strategy, chunk_text, embedding_model, embedding, fts_vector
                ) VALUES (
                    %s, %s, %s, %s,
                    'fixed', %s, 'jina-embeddings-v3', %s, to_tsvector('english', %s)
                );
            """, (title, path, idx, tier, chunk_text, vector, chunk_text))
            total_chunks += 1

        print(f"   ✅ Successfully indexed into pgvector (VECTOR(768)).\n")

    conn.commit()

    # ── SECTION 3: Verify Row Counts & Ingestion Stats ────────────────────────
    print("SECTION 3: Ingestion Verification")
    cur.execute("""
        SELECT access_tier, chunk_strategy, count(*)
        FROM rag.document_chunks
        GROUP BY access_tier, chunk_strategy
        ORDER BY access_tier, chunk_strategy;
    """)
    rows = cur.fetchall()

    print("\nDatabase Row Counts by Access Tier and Strategy:")
    print("┌─────────────┬────────────────┬──────────────┐")
    print("│ Access Tier │ Strategy       │ Chunks Count │")
    print("├─────────────┼────────────────┼──────────────┤")
    for tier, strat, cnt in rows:
        tier_label = f"Tier {tier}"
        print(f"│ {tier_label:<11} │ {strat:<14} │ {cnt:<12} │")
    print("└─────────────┴────────────────┴──────────────┘")

    cur.close()
    conn.close()

    print(f"\nTotal chunks stored: {total_chunks}")
    print(f"Adversarial chunks flagged: {flagged_chunks}")

    print("\n" + DIVIDER)
    print("CLEAN REFERENCE: Ingestion SQL with tsvector generation:")
    print(DIVIDER)
    print("""
INSERT INTO rag.document_chunks (
    doc_title, source_file, chunk_index, access_tier,
    chunk_strategy, chunk_text, embedding_model, embedding, fts_vector
) VALUES (
    %(title)s, %(file)s, %(index)s, %(tier)s,
    'structural', %(text)s, 'jina-embeddings-v3', %(vector_768)s, to_tsvector('english', %(text)s)
);
""")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/03_hybrid_search_and_rrf.py to see Hybrid RRF in action!")


if __name__ == "__main__":
    main()
