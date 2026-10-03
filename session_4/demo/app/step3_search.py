"""
step3_search.py — Pipeline Step 3: Search for Relevant Chunks

Runs a cosine similarity search in pgvector.

Given the query vector from Step 2, this step finds the stored chunk
vectors that are most mathematically similar to it.

HOW IT WORKS:
  1. Every policy chunk was embedded and stored in rag.document_chunks
     during indexing (script 02_index_documents.py).
  2. The <=> operator is pgvector's cosine distance operator.
     Cosine distance = 1 - cosine_similarity.
     → smaller distance = more similar meaning
  3. ORDER BY embedding <=> query_vector LIMIT 3 returns the 3 chunks
     whose vectors are closest to the query vector.

WHY COSINE SIMILARITY:
  Cosine similarity measures the angle between two vectors, not their
  length. This means it captures *direction* (meaning) rather than
  *magnitude* (word frequency). "NVDA beta restriction" and
  "high-volatility equity rule" will be similar even with no shared words.

Usage:
    from app.step3_search import search_chunks

    chunks = search_chunks(query_vector, top_k=3)
    # → [{"chunk_text": "...", "similarity": 0.87}, ...]
"""

import os
import psycopg2


def get_db_connection():
    """Create a Postgres connection using environment variables."""
    return psycopg2.connect(
        host=     os.getenv("DB_HOST",   "localhost"),
        user=     os.getenv("DB_USER",   "ramadugu"),
        password= os.getenv("DB_PASS",   ""),
        port=     int(os.getenv("DB_PORT", "5432")),
        dbname=   os.getenv("DB_NAME", "postgres"),
    )


def search_chunks(query_vector: list[float], top_k: int = 3) -> list[dict]:
    """
    Find the top_k policy chunks most semantically similar to the query vector.

    Args:
        query_vector: A 384-float vector from step2_embed.embed_text().
        top_k:        How many chunks to retrieve (default: 3).

    Returns:
        A list of dicts, sorted by similarity descending (best match first):
          {
            "chunk_text":  str,    # The raw policy text of the chunk
            "similarity":  float,  # Cosine similarity: 0.0 (unrelated) → 1.0 (identical)
          }

    SQL used:
        SELECT chunk_text, 1 - (embedding <=> query_vector) AS similarity
        FROM rag.document_chunks
        ORDER BY embedding <=> query_vector
        LIMIT top_k;
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                chunk_text,
                1 - (embedding <=> %s::vector) AS similarity
            FROM rag.document_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_vector, query_vector, top_k),
        )
        rows = cur.fetchall()
        return [
            {"chunk_text": row[0], "similarity": round(float(row[1]), 4)}
            for row in rows
        ]
    finally:
        conn.close()
