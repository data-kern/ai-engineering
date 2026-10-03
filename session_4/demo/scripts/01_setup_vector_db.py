#!/usr/bin/env python3
"""
Session 4 RAG Demo — Step 1: Set up pgvector in Postgres.

Run this script ONCE before indexing or starting the service.
It creates the schema and the document_chunks table with a VECTOR(384) column.

Usage:
    DB_USER=postgres DB_PASS=postgres python scripts/01_setup_vector_db.py
"""

import os
import psycopg2

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

def pause():
    input("\n🔍 Press ENTER to continue ➔ ")
    print("\n" + "─" * 70)


def setup():
    print("\n" + "=" * 70)
    print("  Session 4 RAG Demo — Step 1: Vector Database Setup")
    print("=" * 70)
    
    print("\nConnecting to Postgres...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # ── Step 1: Enable pgvector ───────────────────────────────────────────────
    print("\nSECTION 1: pgvector Extension")
    print("PREDICT: Before we can store embeddings, Postgres needs to understand vectors.")
    print("What extension needs to be enabled?")
    pause()

    print("Enabling pgvector extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    print("  ✅ pgvector enabled.")
    
    # ── Step 2: Create the rag schema ─────────────────────────────────────────
    print("\nSECTION 2: Schema Creation")
    print("Creating rag schema...")
    cur.execute("CREATE SCHEMA IF NOT EXISTS rag;")
    print("  ✅ Schema 'rag' ready.")

    # ── Step 3: Create the document_chunks table ──────────────────────────────
    print("\nSECTION 3: Document Chunks Table")
    print("PREDICT: We need to store the chunk text and its vector representation.")
    print("If our embedding model (all-MiniLM-L6-v2) outputs 384 dimensions,")
    print("what data type will the embedding column be?")
    pause()

    print("Creating rag.document_chunks table with VECTOR(384)...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rag.document_chunks (
            id          SERIAL PRIMARY KEY,
            source_file TEXT        NOT NULL,
            chunk_index INTEGER     NOT NULL,
            chunk_text  TEXT        NOT NULL,
            embedding   VECTOR(384) NOT NULL
        );
    """)
    print("  ✅ Table rag.document_chunks created.")

    # ── Step 4: Create an HNSW index for fast nearest-neighbour search ────────
    print("\nSECTION 4: HNSW Index")
    print("Without an index, Postgres scans every row (slow).")
    print("With HNSW (Hierarchical Navigable Small World), it uses an approximate graph search (fast).")
    pause()

    print("Creating HNSW index for vector search...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON rag.document_chunks
        USING hnsw (embedding vector_cosine_ops);
    """)
    print("  ✅ HNSW index created.")

    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✅ Database setup complete!")
    print("OBSERVE: Open DBeaver or pgAdmin, connect to 'postgres', and verify:")
    print("  1. The 'rag' schema exists")
    print("  2. The 'document_chunks' table exists")
    print("  3. The 'embedding' column is of type 'USER-DEFINED' or 'vector(384)'")
    print("=" * 70)
    print("\nNext → run python scripts/02_index_documents.py")

if __name__ == "__main__":
    setup()
