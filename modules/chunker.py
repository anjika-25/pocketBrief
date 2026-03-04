"""
Phase 3 — Text Chunking
Splits transcript text into overlapping word-level chunks for embedding.
"""

import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_transcript_file, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def load_transcript(video_id: str, transcript_path: str | None = None) -> str:
    """Load transcript text from file."""
    path = Path(transcript_path) if transcript_path else get_transcript_file(video_id)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found at {path}")
    return path.read_text(encoding="utf-8")


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks based on word count.

    Args:
        text: Full transcript text.
        chunk_size: Number of words per chunk.
        overlap: Number of overlapping words between consecutive chunks.

    Returns:
        List of text chunks.
    """
    words = text.split()
    total_words = len(words)

    if total_words == 0:
        logger.warning("Empty transcript — no chunks produced.")
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < total_words:
        end = min(start + chunk_size, total_words)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += step

    logger.info(
        f"Produced {len(chunks)} chunks from {total_words} words "
        f"(size={chunk_size}, overlap={overlap})"
    )
    return chunks


def load_and_chunk(video_id: str, transcript_path: str | None = None) -> list[str]:
    """Convenience: load transcript then chunk it."""
    text = load_transcript(video_id, transcript_path)
    return chunk_text(text)


if __name__ == "__main__":
    chunks = load_and_chunk()
    for i, c in enumerate(chunks[:3]):
        print(f"--- Chunk {i} ---")
        print(c[:200], "…\n")
    print(f"Total chunks: {len(chunks)}")
