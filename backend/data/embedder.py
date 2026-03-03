"""
Sentence-transformers embedder (all-MiniLM-L6-v2).
Local, free, 384-dim vectors — no rate limits, no API costs.
"""

import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Loaded once at import time
_model = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedder ready.")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of 384-dim float vectors."""
    if not texts:
        return []
    model = get_embedder()
    vectors = model.encode(texts, show_progress_bar=False, batch_size=64)
    return vectors.tolist()


def embed_one(text: str) -> list[float]:
    """Embed a single text string."""
    return embed([text])[0]
