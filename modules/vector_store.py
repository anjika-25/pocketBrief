"""
Phase 5 — Vector Database (FAISS)
Creates, saves, and loads a FAISS index paired with the original text chunks.
"""

import logging
import pickle
from pathlib import Path

import faiss
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_faiss_index_file, get_chunks_file, FAISS_INDEX_DIR, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


def build_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    """
    Build a FAISS L2 index from embedding vectors.

    Args:
        embeddings: Numpy array of shape (n, dim).

    Returns:
        A FAISS IndexFlatL2 instance.
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings.astype(np.float32))
    logger.info(f"FAISS index built — {index.ntotal} vectors, dim={dim}")
    return index


def save_index(index: faiss.IndexFlatL2, chunks: list[str], video_id: str) -> None:
    """Persist the FAISS index and chunk list to disk."""
    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index_file = get_faiss_index_file(video_id)
    chunks_file = get_chunks_file(video_id)
    
    faiss.write_index(index, str(index_file))
    with open(chunks_file, "wb") as f:
        pickle.dump(chunks, f)
    logger.info(f"Index saved to {index_file}")
    logger.info(f"Chunks saved to {chunks_file}")


def load_index(video_id: str) -> tuple[faiss.IndexFlatL2, list[str]]:
    """Load the FAISS index and associated chunks from disk."""
    index_file = get_faiss_index_file(video_id)
    chunks_file = get_chunks_file(video_id)
    
    if not index_file.exists():
        raise FileNotFoundError(f"FAISS index not found at {index_file}")
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found at {chunks_file}")

    index = faiss.read_index(str(index_file))
    with open(chunks_file, "rb") as f:
        chunks = pickle.load(f)

    logger.info(f"Loaded index ({index.ntotal} vectors) and {len(chunks)} chunks")
    return index, chunks


if __name__ == "__main__":
    # Quick smoke test
    dummy = np.random.rand(5, EMBEDDING_DIMENSION).astype(np.float32)
    idx = build_index(dummy)
    save_index(idx, [f"chunk_{i}" for i in range(5)])
    idx2, ch2 = load_index()
    print(f"Loaded {idx2.ntotal} vectors, {len(ch2)} chunks")
