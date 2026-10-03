"""
step2_embed.py — Pipeline Step 2: Embed the Question

Converts a text string into a 384-dimensional vector (a list of 384 floats).
This vector is a mathematical representation of the text's meaning.

WHY: Two pieces of text that mean the same thing will produce vectors
that are close to each other in this 384-dimensional space — even if
the words are different. This is what makes semantic search possible.

IMPORTANT: The same model (all-MiniLM-L6-v2) was used to embed every
chunk during indexing (script 02). You MUST use the same model here.
If you embed with model A and search against chunks embedded with model B,
the vectors are in different mathematical spaces and distances mean nothing.

Usage:
    from app.step2_embed import embed_text

    vector = embed_text("Should Mr. Peterson add more NVDA?")
    # → a list of 384 floats
"""

from sentence_transformers import SentenceTransformer

# Module-level holder — the model is loaded once per process, on first use.
# This is called lazy loading: the model only loads when embed_text() is
# called for the first time, not when the module is imported.
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the embedding model, loading it on first call."""
    global _model
    if _model is None:
        print("[Step 2] Loading embedding model (all-MiniLM-L6-v2)...")
        print("         First run downloads ~80MB. Subsequent runs are instant.")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Step 2] Embedding model ready.")
    return _model


def embed_text(text: str) -> list[float]:
    """
    Convert a text string into a 384-dimensional embedding vector.

    Args:
        text: Any string — a question, a sentence, or a document chunk.

    Returns:
        A list of 384 floats. Each float is one dimension of the
        text's position in embedding space.

    Example:
        vector = embed_text("Conservative client risk rules")
        # → [0.041, -0.127, 0.038, 0.092, ..., -0.019]  (384 values)
    """
    model = _get_model()
    return model.encode(text).tolist()
