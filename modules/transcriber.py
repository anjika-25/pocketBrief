"""
Phase 2 — Transcription
Uses Groq's cloud Whisper API for fast video transcription.
Handles long videos by splitting audio into chunks under the 25 MB API limit.
Falls back to local Whisper for short voice queries.
"""

import logging
import os
import subprocess
import shutil
import time
from pathlib import Path

from groq import Groq

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    WHISPER_MODEL, TRANSCRIPT_DIR,
    GROQ_API_KEY, AUDIO_DIR, get_audio_file, get_transcript_file
)

logger = logging.getLogger(__name__)

# Groq Whisper has a 25 MB file-size limit — we target 20 MB per chunk to stay safe
_GROQ_MAX_BYTES = 25 * 1024 * 1024
_CHUNK_TARGET_BYTES = 20 * 1024 * 1024   # 20 MB per segment
_GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

# ─── ffmpeg helper ────────────────────────────────────────────────────────────

_KNOWN_FFMPEG_DIR = Path.home() / (
    r"AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.0.1-full_build\bin"
)


def _ffmpeg_bin() -> str:
    """Return path to ffmpeg executable."""
    known = _KNOWN_FFMPEG_DIR / "ffmpeg.exe"
    if known.is_file():
        return str(known)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError("ffmpeg not found — needed to compress audio for Groq API")


def _get_duration_seconds(src: str) -> float:
    """Use ffprobe to get the duration of an audio file in seconds."""
    ffmpeg = _ffmpeg_bin()
    ffprobe = str(Path(ffmpeg).parent / "ffprobe.exe")
    if not Path(ffprobe).is_file():
        ffprobe = shutil.which("ffprobe") or ffprobe

    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", src],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def _compress_audio(src: str, dst: str, start_sec: float = 0.0, duration_sec: float | None = None) -> str:
    """
    Compress audio to mono 16 kHz MP3 at 32 kbps.
    Optionally extract only a slice [start_sec, start_sec + duration_sec].
    """
    ffmpeg = _ffmpeg_bin()
    cmd = [ffmpeg, "-y"]
    if start_sec > 0:
        cmd += ["-ss", str(start_sec)]
    cmd += ["-i", src]
    if duration_sec is not None:
        cmd += ["-t", str(duration_sec)]
    cmd += [
        "-ac", "1",      # mono
        "-ar", "16000",  # 16 kHz
        "-b:a", "32k",   # 32 kbps
        dst,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    size_mb = os.path.getsize(dst) / 1e6
    logger.info("Compressed segment → %s (%.1f MB)", dst, size_mb)
    return dst


# ─── Groq cloud transcription ────────────────────────────────────────────────

def _call_groq_api(file_path: str, time_offset: float = 0.0) -> list[dict]:
    """
    Send one audio file to Groq Whisper and return a list of segment dicts
    with timestamps already shifted by time_offset seconds.
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Sending '%s' to Groq Whisper API…", Path(file_path).name)

        with open(file_path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(Path(file_path).name, f),
                model=_GROQ_WHISPER_MODEL,
                response_format="verbose_json",
                language="en",
                temperature=0.0,
            )

        segments = []
        for seg in getattr(result, "segments", []) or []:
            segments.append({
                "start": seg.get("start", 0) + time_offset,
                "end":   seg.get("end",   0) + time_offset,
                "text":  seg.get("text",  "").strip(),
            })

        # Fallback: treat the whole result as one big segment
        if not segments:
            text = (getattr(result, "text", "") or "").strip()
            if text:
                segments.append({"start": time_offset, "end": time_offset, "text": text})

        return segments

    except Exception as e:
        if "429" in str(e) or "rate_limit_exceeded" in str(e).lower():
            logger.warning("Groq Rate Limit (429) hit. Falling back to LOCAL Whisper model...")
            return _transcribe_locally(file_path, time_offset)
        raise e


def _transcribe_locally(file_path: str, time_offset: float = 0.0) -> list[dict]:
    """
    Fallback transcription using local OpenAI Whisper library.
    Used when API limits are reached.
    """
    try:
        import whisper
        import os
        from pathlib import Path
        # Ensure ffmpeg is implicitly on PATH for OpenAI whisper module
        ffmpeg_dir = str(_KNOWN_FFMPEG_DIR)
        if ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + ffmpeg_dir

        # Load model (lazy loading)
        logger.info("Loading local Whisper '%s' model... (this may take a moment)", WHISPER_MODEL)
        model = whisper.load_model(WHISPER_MODEL)
        
        logger.info("Transcribing '%s' locally...", Path(file_path).name)
        result = model.transcribe(file_path, language="en", temperature=0.0)
        
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"] + time_offset,
                "end":   seg["end"] + time_offset,
                "text":  seg["text"].strip(),
            })
            
        return segments
    except Exception as local_err:
        logger.error("Local Whisper fallback failed: %s", local_err)
        raise Exception(f"Transcription failed: Groq Rate Limit exceeded and local fallback failed. {local_err}")


def _transcribe_via_groq(audio_path: str) -> list[dict]:
    """
    Transcribe an audio file using Groq Whisper.

    Strategy:
    1. Compress the whole file to a small MP3.
    2. If it fits in one call (≤ 20 MB), send it directly.
    3. If it's still too large, calculate how many seconds fit in 20 MB
       and split the file into N equal-duration chunks, transcribing each.
    Returns a flat list of segment dicts with global timestamps.
    """
    # ── Step 1: compress ──────────────────────────────────────────────────────
    compressed_path = str(AUDIO_DIR / "video_compressed.mp3")
    _compress_audio(audio_path, compressed_path)
    compressed_size = os.path.getsize(compressed_path)

    # ── Step 2: single-shot if small enough ───────────────────────────────────
    if compressed_size <= _CHUNK_TARGET_BYTES:
        logger.info("Audio fits in one Groq call (%.1f MB) — transcribing…", compressed_size / 1e6)
        return _call_groq_api(compressed_path, time_offset=0.0)

    # ── Step 3: split into chunks ─────────────────────────────────────────────
    total_duration = _get_duration_seconds(compressed_path)
    # bytes-per-second at current bitrate, then figure out how many seconds → 20 MB
    bytes_per_sec = compressed_size / total_duration
    chunk_duration = _CHUNK_TARGET_BYTES / bytes_per_sec   # seconds per chunk

    n_chunks = int(total_duration / chunk_duration) + 1
    logger.info(
        "Audio is %.1f MB / %.0f s — splitting into %d chunks of ~%.0f s each…",
        compressed_size / 1e6, total_duration, n_chunks, chunk_duration
    )

    all_segments: list[dict] = []
    chunks_dir = AUDIO_DIR / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n_chunks):
        start = i * chunk_duration
        if start >= total_duration:
            break

        chunk_path = str(chunks_dir / f"chunk_{i:03d}.mp3")
        _compress_audio(
            compressed_path, chunk_path,
            start_sec=start,
            duration_sec=chunk_duration,
        )

        chunk_size = os.path.getsize(chunk_path)
        logger.info("Chunk %d/%d — %.1f MB, offset %.0f s", i + 1, n_chunks, chunk_size / 1e6, start)

        try:
            segs = _call_groq_api(chunk_path, time_offset=start)
            all_segments.extend(segs)
        except Exception as e:
            logger.warning("Chunk %d failed (%s) — skipping", i + 1, e)

        # Small delay to avoid hammering the API
        time.sleep(0.5)

    # Clean up chunk files
    shutil.rmtree(chunks_dir, ignore_errors=True)

    return all_segments


# ─── Public API ──────────────────────────────────────────────────────────────

def transcribe_audio(video_id: str, audio_path: str | None = None) -> str:
    """
    Transcribe audio using Groq's cloud Whisper API.
    Automatically handles files of any length by splitting into chunks.

    Args:
        video_id: Unique identifier for the video.
        audio_path: Path to the audio file. Defaults to config get_audio_file(video_id).

    Returns:
        Path to the saved transcript file.
    """
    audio_path = audio_path or str(get_audio_file(video_id))
    logger.info("Transcribing full video: %s", audio_path)

    segments = _transcribe_via_groq(audio_path)

    # Build transcript with timestamps
    if segments:
        lines = [
            f"[{_format_time(s['start'])} -> {_format_time(s['end'])}]  {s['text']}"
            for s in segments if s.get("text")
        ]
        transcript_text = "\n".join(lines)
    else:
        transcript_text = "[No transcript could be generated]"

    # Save to file
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    transcript_file = get_transcript_file(video_id)
    transcript_file.write_text(transcript_text, encoding="utf-8")

    logger.info("Transcript saved to: %s", transcript_file)
    return str(transcript_file)


def transcribe_query(audio_path: str) -> str:
    """
    Transcribe a short voice query via Groq Whisper API.
    """
    logger.info("Transcribing mic query: %s", audio_path)
    file_size = os.path.getsize(audio_path)

    # For short queries, compress if needed then send directly
    if file_size > _GROQ_MAX_BYTES:
        compressed = str(AUDIO_DIR / "query_compressed.mp3")
        _compress_audio(audio_path, compressed)
        audio_path = compressed

    segments = _call_groq_api(audio_path, time_offset=0.0)
    return " ".join(s["text"] for s in segments).strip()


def _format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


if __name__ == "__main__":
    path = transcribe_audio("test")
    print(f"Transcript saved: {path}")
