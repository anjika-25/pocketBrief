"""
Phase 6 — Retrieval
Embeds a user question, searches FAISS, and returns the top-k relevant chunks.
"""

import logging
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TOP_K
from modules.embedder import embed_query
from modules.vector_store import load_index

logger = logging.getLogger(__name__)


def retrieve(question: str, video_id: str, top_k: int = TOP_K) -> list[str]:
    """
    Retrieve the most relevant transcript chunks for a question.

    Args:
        question: User's natural-language question.
        video_id: Unique identifier for the video.
        top_k: Number of chunks to retrieve.

    Returns:
        List of the top-k most relevant text chunks.
    """
    # 1. Embed the question
    query_vec = embed_query(question).reshape(1, -1).astype(np.float32)

    # 2. Load FAISS index + chunks
    index, chunks = load_index(video_id)

    # 3. Search
    distances, indices = index.search(query_vec, top_k)
    logger.info(f"Retrieval distances: {distances[0].tolist()}")

    # 4. Gather results (filter out -1 which indicates padding)
    results: list[str] = []
    for idx in indices[0]:
        if 0 <= idx < len(chunks):
            results.append(chunks[idx])

    logger.info(f"Retrieved {len(results)} chunks for question: {question[:80]}…")
    return results


if __name__ == "__main__":
    q = "What is the main topic of this lecture?"
    try:
        docs = retrieve(q)
        for i, d in enumerate(docs):
            print(f"\n--- Chunk {i} ---")
            print(d[:300])
    except FileNotFoundError as e:
        print(f"Index not built yet: {e}")
