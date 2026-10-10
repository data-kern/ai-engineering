#!/usr/bin/env python3
"""
DataKern AI Engineering — Session 5 Demo
Script 01: Enterprise Database Setup — Upgrading pgvector with Full-Text Search and Access Control

What you will learn:
  1. Why Enterprise RAG requires both semantic vectors AND full-text search indexes
  2. How to create a GIN index on PostgreSQL tsvector columns for sub-millisecond keyword retrieval
  3. How to add an access_tier column to enforce security at the database layer (Slide 12)
  4. How HNSW and GIN indexes coexist within the same table

Usage:
  python scripts/01_setup_enterprise_db.py
"""

import os
import psycopg2

# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Helpers
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", os.getenv("USER", "ramadugu")),
    "password": os.getenv("DB_PASS", ""),
    "port":     os.getenv("DB_PORT", "5432"),
    "dbname":   os.getenv("DB_NAME", "postgres"),
}

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
    print("  DATAKERN SESSION 5: SCRIPT 01 — ENTERPRISE DATABASE SETUP")
    print(DIVIDER)
    print("""
THE ARCHITECTURAL SHIFT:
- In Session 4:
    We created rag.document_chunks with only: (chunk_text, embedding).
    Every query ran a pure Top-K vector scan across all chunks without security.
- In Session 5 (Enterprise RAG):
    We add:
      1. 'access_tier' (INT): Enforces authorization directly in SQL.
      2. 'fts_vector' (TSVECTOR): Enables BM25-style keyword matching for identifiers.
      3. 'chunk_strategy' (TEXT): Distinguishes structural vs fixed-size chunking.
      4. 'doc_title' (TEXT): Preserves source document metadata.
""")
    pause()

    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    print("✅ Connected to PostgreSQL successfully.\n")

    # ── SECTION 1: Enable Extensions ─────────────────────────────────────────
    print("SECTION 1: Vector Extension Check")
    print("PREDICT: Does pgvector need to be enabled before creating VECTOR columns?")
    pause()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("CREATE SCHEMA IF NOT EXISTS rag;")
    print("✅ Extension 'vector' verified and schema 'rag' ready.")

    # ── SECTION 2: Create Enterprise Document Chunks Table ────────────────────
    print("\nSECTION 2: Enterprise Schema Migration")
    print("PREDICT: What happens to existing queries if we add columns with DEFAULT values?")
    print("Will existing Session 4 data break, or can we upgrade transparently?")
    pause()

    print("Creating or upgrading rag.document_chunks table with VECTOR(768)...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rag.document_chunks (
            id              SERIAL PRIMARY KEY,
            doc_title       TEXT NOT NULL DEFAULT 'Apex Risk Policy',
            source_file     TEXT NOT NULL,
            chunk_index     INTEGER NOT NULL,
            access_tier     INTEGER NOT NULL DEFAULT 1,
            chunk_strategy  TEXT NOT NULL DEFAULT 'structural',
            chunk_text      TEXT NOT NULL,
            embedding_model TEXT NOT NULL DEFAULT 'jina-embeddings-v3',
            embedding       VECTOR(768) NOT NULL,
            fts_vector      TSVECTOR
        );
    """)

    # Ensure all columns exist and embedding column is VECTOR(768)
    cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN IF NOT EXISTS doc_title TEXT NOT NULL DEFAULT 'Apex Policy';")
    cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN IF NOT EXISTS access_tier INTEGER NOT NULL DEFAULT 1;")
    cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN IF NOT EXISTS chunk_strategy TEXT NOT NULL DEFAULT 'structural';")
    cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'jina-embeddings-v3';")
    cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN IF NOT EXISTS fts_vector TSVECTOR;")

    # Check if existing embedding column has 384 dimensions; if so, upgrade to VECTOR(768)
    cur.execute("""
        SELECT atttypmod FROM pg_attribute
        WHERE attrelid = 'rag.document_chunks'::regclass AND attname = 'embedding';
    """)
    row = cur.fetchone()
    if row and row[0] != 768:
        print("  Upgrading embedding column dimension from 384 to 768 (Jina v3)...")
        cur.execute("DROP INDEX IF EXISTS rag.document_chunks_embedding_idx;")
        cur.execute("ALTER TABLE rag.document_chunks DROP COLUMN IF EXISTS embedding;")
        cur.execute("ALTER TABLE rag.document_chunks ADD COLUMN embedding VECTOR(768) NOT NULL DEFAULT (array_fill(0.0, ARRAY[768]))::vector;")
        cur.execute("ALTER TABLE rag.document_chunks ALTER COLUMN embedding DROP DEFAULT;")

    print("✅ Table rag.document_chunks upgraded to Enterprise Schema (VECTOR(768) for Jina AI).")

    # ── SECTION 3: The Two Indexes (HNSW for Vectors, GIN for Text) ───────────
    print("\nSECTION 3: Dual-Index Strategy (HNSW + GIN)")
    print("PREDICT: We have two search modalities. Which index accelerates keyword text search?")
    print("  A) B-Tree")
    print("  B) GIN (Generalized Inverted Index)")
    print("  C) HNSW")
    pause()

    print("Answer: B) GIN Index. GIN maps every individual word token to the rows")
    print("that contain it, enabling sub-millisecond keyword lookup.\n")

    print("Building HNSW vector index (for semantic similarity)...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON rag.document_chunks
        USING hnsw (embedding vector_cosine_ops);
    """)
    print("  ✅ HNSW index active: document_chunks_embedding_idx")

    print("Building GIN full-text search index (for exact token matching)...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_fts_idx
        ON rag.document_chunks
        USING gin (fts_vector);
    """)
    print("  ✅ GIN index active: document_chunks_fts_idx")

    print("Building B-Tree index on access_tier (for instant security scoping)...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_access_tier_idx
        ON rag.document_chunks (access_tier);
    """)
    print("  ✅ B-Tree index active: document_chunks_access_tier_idx")

    cur.close()
    conn.close()

    # ── SECTION 4: Clean Reference DDL ────────────────────────────────────────
    print("\n" + DIVIDER)
    print("CLEAN REFERENCE DDL (Copy-paste this for production migrations):")
    print(DIVIDER)
    print("""
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.document_chunks (
    id              SERIAL PRIMARY KEY,
    doc_title       TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    access_tier     INTEGER NOT NULL DEFAULT 1,  -- 1=Public, 3=Client Data, 4=Compliance
    chunk_strategy  TEXT NOT NULL DEFAULT 'structural',
    chunk_text      TEXT NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT 'jina-embeddings-v3',
    embedding       VECTOR(768) NOT NULL,        -- Jina Embeddings v3 (768 dimensions)
    fts_vector      TSVECTOR
);

-- Index 1: HNSW for Cosine Vector Similarity (768 dimensions)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON rag.document_chunks USING hnsw (embedding vector_cosine_ops);

-- Index 2: GIN for Full-Text Search (tsvector @@ query)
CREATE INDEX IF NOT EXISTS document_chunks_fts_idx
ON rag.document_chunks USING gin (fts_vector);

-- Index 3: B-Tree for Access Scoping (WHERE access_tier <= user_tier)
CREATE INDEX IF NOT EXISTS document_chunks_access_tier_idx
ON rag.document_chunks (access_tier);
""")
    print(DIVIDER)
    print("OBSERVE: Verify in DBeaver, TablePlus, or psql that all 3 indexes exist:")
    print("  SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'rag';")
    print(DIVIDER)
    print("Next step ➔ Run python scripts/02_index_enterprise_docs.py to ingest multi-tier documents.")


if __name__ == "__main__":
    main()
