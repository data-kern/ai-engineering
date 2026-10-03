#!/usr/bin/env python3
"""
Session 4 RAG Demo — Step 2: Index Documents into pgvector.

This script reads the policy document, splits it into chunks,
embeds each chunk using a local embedding model, and stores
everything in the rag.document_chunks table.

Run this ONCE after running 01_setup_vector_db.py.

Usage:
    DB_USER=postgres DB_PASS=postgres python scripts/02_index_documents.py
"""

import os
import psycopg2
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "ramadugu"),
    "password": os.getenv("DB_PASS", ""),
    "port":     os.getenv("DB_PORT", "5432"),
    "dbname":   os.getenv("DB_NAME", "postgres"),
}

DOCUMENTS = [
    "data/apex_risk_policy.txt",
]

CHUNK_SIZE = 300    # words per chunk
OVERLAP    = 50     # words shared between adjacent chunks

def pause():
    input("\n🔍 Press ENTER to continue ➔ ")
    print("\n" + "─" * 70)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words  = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def index_document(filepath: str, conn, embed_model):
    print(f"\nIndexing: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"  → Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={OVERLAP})")

    cur = conn.cursor()
    cur.execute("DELETE FROM rag.document_chunks WHERE source_file = %s", (filepath,))

    for idx, chunk in enumerate(chunks):
        vector = embed_model.encode(chunk).tolist()
        cur.execute(
            """
            INSERT INTO rag.document_chunks (source_file, chunk_index, chunk_text, embedding)
            VALUES (%s, %s, %s, %s)
            """,
            (filepath, idx, chunk, vector),
        )
        if (idx + 1) % 10 == 0 or (idx + 1) == len(chunks):
            print(f"  → Embedded and stored chunk {idx + 1}/{len(chunks)}", end="\r")

    conn.commit()
    cur.close()
    print(f"\n  ✅ {len(chunks)} chunks stored for {filepath}")


def main():
    print("\n" + "=" * 70)
    print("  Session 4 RAG Demo — Step 2: Document Indexer")
    print("=" * 70)

    print("\nSECTION 1: Load Embedding Model")
    print("PREDICT: We are using a local model 'all-MiniLM-L6-v2'.")
    print("Will it need an API key to generate vectors?")
    pause()

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("  ✅ Embedding model loaded (Local execution, no API key).")

    print("\nSECTION 2: Chunk & Embed")
    print("PREDICT: The policy document will be split into overlapping chunks.")
    print("Why do we need overlap between adjacent chunks?")
    pause()
    
    print("  Answer: Overlap prevents critical sentences from being split in half,")
    print("  preserving context across chunk boundaries.\n")

    conn = psycopg2.connect(**DB_CONFIG)

    for doc_path in DOCUMENTS:
        if not os.path.exists(doc_path):
            print(f"  ⚠️  File not found: {doc_path} — skipping.")
            continue
        index_document(doc_path, conn, embed_model)

    conn.close()

    print("\nSECTION 3: Verify the Data")
    pause()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rag.document_chunks;")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print(f"✅ Indexing complete!")
    print(f"Total rows in rag.document_chunks: {total}")
    
    print("\nOBSERVE: Open DBeaver and run:")
    print("  SELECT chunk_index, chunk_text, embedding")
    print("  FROM rag.document_chunks LIMIT 5;")
    print("\nYou will see the embedding column contains 384 numbers per row.")
    print("These vectors represent the semantic meaning of each chunk.")
    print("=" * 70)
    
    print("\nNext → run python scripts/03_rag_pipeline_walkthrough.py")


if __name__ == "__main__":
    main()
