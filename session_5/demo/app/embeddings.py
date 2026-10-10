"""
DataKern Session 5 Demo — Hosted Embedding Service
Strictly adheres to DataKern Assignment 4 requirements:
- Uses hosted embedding APIs over HTTPS (no local sentence-transformers, no fake vectors).
- Supports Jina AI (default: jina-embeddings-v3, dimensions=768) and Google Gemini (768 dimensions).
- Uses asymmetric retrieval tasks:
    - 'retrieval.passage' / 'RETRIEVAL_DOCUMENT' for indexed document chunks
    - 'retrieval.query' / 'RETRIEVAL_QUERY' for search questions
- Fails fast with clear error instructions if API keys are missing or requests fail.
"""

import os
from typing import List
import requests

JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_DEFAULT_MODEL = "jina-embeddings-v3"
EMBEDDING_DIM = 768


def _embed_jina(texts: List[str], purpose: str) -> List[List[float]]:
    """Calls Jina AI embeddings v3 API over HTTPS."""
    api_key = os.getenv("JINA_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "\n❌ [Authentication Error] JINA_API_KEY is not set.\n"
            "   As taught in DataKern Assignment 4, real embeddings require an active API key.\n"
            "   Please export your key in the terminal before running:\n"
            "     export JINA_API_KEY=\"your_jina_key_here\"\n"
            "   (Get a key at https://jina.ai/embeddings)\n"
        )

    task = "retrieval.passage" if purpose.lower() in ("document", "passage") else "retrieval.query"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
    }

    # Batch in groups of 32
    batch_size = 32
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        payload = {
            "model": JINA_DEFAULT_MODEL,
            "task": task,
            "dimensions": EMBEDDING_DIM,
            "normalized": True,
            "embedding_type": "float",
            "input": batch,
        }

        try:
            resp = requests.post(JINA_API_URL, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error while connecting to Jina AI API: {e}") from e

        if resp.status_code != 200:
            raise RuntimeError(
                f"Jina AI API returned HTTP {resp.status_code}:\n{resp.text}\n"
                f"Verify your JINA_API_KEY and account quota."
            )

        data = resp.json().get("data", [])
        data_sorted = sorted(data, key=lambda item: item.get("index", 0))

        if len(data_sorted) != len(batch):
            raise RuntimeError(
                f"Jina API returned {len(data_sorted)} embeddings for a batch of {len(batch)} items."
            )

        for item in data_sorted:
            emb = item.get("embedding", [])
            if len(emb) != EMBEDDING_DIM:
                raise ValueError(
                    f"Vector dimension mismatch from Jina API: expected {EMBEDDING_DIM}, received {len(emb)}."
                )
            all_embeddings.append(emb)

    return all_embeddings


def _embed_gemini(texts: List[str], purpose: str) -> List[List[float]]:
    """Calls Google Gemini Embedding API with 768 output dimensions."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "\n❌ [Authentication Error] GEMINI_API_KEY is not set.\n"
            "   Please export your key in the terminal before running:\n"
            "     export GEMINI_API_KEY=\"your_gemini_key_here\"\n"
        )

    task_type = "RETRIEVAL_DOCUMENT" if purpose.lower() in ("document", "passage") else "RETRIEVAL_QUERY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={api_key.strip()}"

    requests_payload = [
        {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": t}]},
            "taskType": task_type,
            "outputDimensionality": EMBEDDING_DIM,
        }
        for t in texts
    ]

    resp = requests.post(url, json={"requests": requests_payload}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json().get("embeddings", [])
    embeddings = [item.get("values", []) for item in data]
    for emb in embeddings:
        if len(emb) != EMBEDDING_DIM:
            raise ValueError(f"Gemini vector dimension mismatch: expected {EMBEDDING_DIM}, got {len(emb)}")
    return embeddings


def embed_texts(texts: List[str], purpose: str = "query") -> List[List[float]]:
    """
    Embeds a list of texts using the configured hosted embedding provider.

    Args:
        texts: List of strings to embed.
        purpose: "document" (passage indexing) or "query" (retrieval search).

    Returns:
        List of 768-dimensional float vectors.
    """
    if not texts:
        return []

    provider = os.getenv("EMBEDDING_PROVIDER", "jina").lower().strip()
    if provider == "gemini":
        return _embed_gemini(texts, purpose=purpose)
    elif provider == "jina":
        return _embed_jina(texts, purpose=purpose)
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER '{provider}'. Supported: 'jina', 'gemini'.")


def embed_single(text: str, purpose: str = "query") -> List[float]:
    """Convenience helper for a single text string."""
    vectors = embed_texts([text], purpose=purpose)
    return vectors[0]
