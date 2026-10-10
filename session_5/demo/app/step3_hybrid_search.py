"""
DataKern Session 5 Demo — Step 3: Hybrid Search with Reciprocal Rank Fusion (RRF)
and Database-Level Access Control (Slides 5, 6, 11, and 12).
"""

import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.embeddings import embed_single


def get_db_connection():
    db_config = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "user":     os.getenv("DB_USER", os.getenv("USER", "ramadugu")),
        "password": os.getenv("DB_PASS", ""),
        "port":     os.getenv("DB_PORT", "5432"),
        "dbname":   os.getenv("DB_NAME", "postgres"),
    }
    return psycopg2.connect(**db_config)


def search_enterprise_chunks(
    query_text: str,
    user_tier: int = 1,
    top_k: int = 3,
    chunk_strategy: str = "structural",
    mode: str = "hybrid",
    conn = None
) -> List[Dict[str, Any]]:
    """
    Executes access-scoped retrieval using pure vector, pure keyword, or RRF hybrid search.

    Modes:
        - "hybrid": Reciprocal Rank Fusion of Vector and Full-Text Search (Slide 6)
        - "vector": Pure vector search with pgvector (Assignment 4 baseline)
        - "keyword": Pure PostgreSQL Full-Text Search (ts_rank)
    """
    should_close_conn = False
    if conn is None:
        conn = get_db_connection()
        should_close_conn = True

    try:
        query_vector = embed_single(query_text, purpose="query")

        cur = conn.cursor(cursor_factory=RealDictCursor)

        if mode == "vector":
            # Baseline: Pure Vector Search (Scoped by Access Tier)
            sql = """
                SELECT
                    id,
                    doc_title,
                    access_tier,
                    chunk_text,
                    (1 - (embedding <=> %(query_vector)s::vector)) AS similarity,
                    ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_vector)s::vector) AS vector_rank,
                    NULL::INTEGER AS keyword_rank,
                    (1.0 / (60 + ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_vector)s::vector))) AS rrf_score
                FROM rag.document_chunks
                WHERE chunk_strategy = %(strategy)s
                  AND access_tier <= %(user_tier)s
                ORDER BY embedding <=> %(query_vector)s::vector
                LIMIT %(top_k)s;
            """
            cur.execute(sql, {
                "query_vector": query_vector,
                "strategy": chunk_strategy,
                "user_tier": user_tier,
                "top_k": top_k
            })
            results = cur.fetchall()

        elif mode == "keyword":
            # Keyword Full-Text Search
            sql = """
                SELECT
                    id,
                    doc_title,
                    access_tier,
                    chunk_text,
                    ts_rank(fts_vector, plainto_tsquery('english', %(query_text)s)) AS keyword_score,
                    NULL::INTEGER AS vector_rank,
                    ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, plainto_tsquery('english', %(query_text)s)) DESC) AS keyword_rank,
                    (1.0 / (60 + ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, plainto_tsquery('english', %(query_text)s)) DESC))) AS rrf_score
                FROM rag.document_chunks
                WHERE chunk_strategy = %(strategy)s
                  AND access_tier <= %(user_tier)s
                  AND fts_vector @@ plainto_tsquery('english', %(query_text)s)
                ORDER BY keyword_rank ASC
                LIMIT %(top_k)s;
            """
            cur.execute(sql, {
                "query_text": query_text,
                "strategy": chunk_strategy,
                "user_tier": user_tier,
                "top_k": top_k
            })
            results = cur.fetchall()

        else:
            # Topic 1: Reciprocal Rank Fusion (Slide 6) + Access Control (Slide 12)
            sql = """
                WITH vector_ranked AS (
                    SELECT
                        id,
                        doc_title,
                        access_tier,
                        chunk_text,
                        ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_vector)s::vector) AS rank
                    FROM rag.document_chunks
                    WHERE chunk_strategy = %(strategy)s
                      AND access_tier <= %(user_tier)s
                    LIMIT 50
                ),
                keyword_ranked AS (
                    SELECT
                        id,
                        doc_title,
                        access_tier,
                        chunk_text,
                        ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, plainto_tsquery('english', %(query_text)s)) DESC) AS rank
                    FROM rag.document_chunks
                    WHERE chunk_strategy = %(strategy)s
                      AND access_tier <= %(user_tier)s
                      AND fts_vector @@ plainto_tsquery('english', %(query_text)s)
                    LIMIT 50
                ),
                combined AS (
                    SELECT
                        COALESCE(v.id, k.id) AS id,
                        COALESCE(v.doc_title, k.doc_title) AS doc_title,
                        COALESCE(v.access_tier, k.access_tier) AS access_tier,
                        COALESCE(v.chunk_text, k.chunk_text) AS chunk_text,
                        v.rank AS vector_rank,
                        k.rank AS keyword_rank,
                        -- Reciprocal Rank Fusion Formula: 1/(k + rank_v) + 1/(k + rank_k) with k=60
                        COALESCE(1.0 / (60 + v.rank), 0.0) +
                        COALESCE(1.0 / (60 + k.rank), 0.0) AS rrf_score
                    FROM vector_ranked v
                    FULL OUTER JOIN keyword_ranked k ON v.id = k.id
                )
                SELECT
                    id,
                    doc_title,
                    access_tier,
                    chunk_text,
                    vector_rank,
                    keyword_rank,
                    rrf_score
                FROM combined
                ORDER BY rrf_score DESC
                LIMIT %(top_k)s;
            """
            cur.execute(sql, {
                "query_vector": query_vector,
                "query_text": query_text,
                "strategy": chunk_strategy,
                "user_tier": user_tier,
                "top_k": top_k
            })
            results = cur.fetchall()

        cur.close()
        return [dict(r) for r in results]

    finally:
        if should_close_conn and conn:
            conn.close()
