"""
Phase 4 — Embeddings
Generates embedding vectors for text chunks using sentence-transformers.
"""

import logging
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Module-level cache so the model is loaded at most once per process
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load and cache the embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_chunks(chunks: list[str]) -> np.ndarray:
    """
    Generate embedding vectors for a list of text chunks.

    Args:
        chunks: List of text strings.

    Returns:
        Numpy array of shape (n_chunks, embedding_dim).
    """
    model = _get_model()
    logger.info(f"Embedding {len(chunks)} chunks…")
    embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings


def embed_query(query: str) -> np.ndarray:
    """
    Generate an embedding vector for a single query string.

    Args:
        query: The user's question.

    Returns:
        Numpy array of shape (embedding_dim,).
    """
    model = _get_model()
    return model.encode(query, convert_to_numpy=True)


if __name__ == "__main__":
    sample = ["Hello world", "Machine learning is great", "Transformers rock"]
    embs = embed_chunks(sample)
    print(f"Shape: {embs.shape}")
