"""
Phase 1 — YouTube Audio Download
Downloads audio from a YouTube URL using yt-dlp Python API and converts to WAV.
"""

import logging
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import AUDIO_DIR, get_audio_file

logger = logging.getLogger(__name__)

# ─── Locate ffmpeg ────────────────────────────────────────────────────────────
# Try well-known WinGet install path first, then fall back to PATH lookup.
_KNOWN_FFMPEG_DIR = Path.home() / (
    r"AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.0.1-full_build\bin"
)


def _find_ffmpeg_location() -> str | None:
    """Return the directory containing ffmpeg/ffprobe, or None."""
    # 1. Check the known WinGet path
    if (_KNOWN_FFMPEG_DIR / "ffmpeg.exe").is_file():
        return str(_KNOWN_FFMPEG_DIR)
    # 2. Fall back to whatever is on PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return str(Path(ffmpeg_path).parent)
    return None


def download_audio(url: str, video_id: str) -> str:
    """
    Download audio from a YouTube video and save as WAV.

    Uses the yt_dlp Python API directly (no subprocess) so we don't
    depend on yt-dlp being on the system PATH.

    Args:
        url: YouTube video URL.
        video_id: Unique identifier for the video.

    Returns:
        Path to the downloaded WAV file.
    """
    import yt_dlp  # imported here to keep module-level import lightweight

    logger.info(f"Downloading audio from: {url}")

    # Ensure output directory exists
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_file = get_audio_file(video_id)

    # yt-dlp needs the target without the extension (it adds .wav)
    output_template = str(AUDIO_DIR / f"{video_id}.%(ext)s")

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "force_overwrites": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        # Enable Node.js as JS runtime (deno isn't installed)
        "js_runtimes": {"node": {}},
    }

    # Point yt-dlp at ffmpeg if we can find it
    ffmpeg_dir = _find_ffmpeg_location()
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
        logger.info("Using ffmpeg from: %s", ffmpeg_dir)
    else:
        logger.warning(
            "ffmpeg not found! Audio conversion will fail. "
            "Install ffmpeg or set --ffmpeg-location."
        )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error("yt-dlp download failed: %s", e)
        raise RuntimeError(f"Failed to download audio: {e}") from e

    # Verify output exists
    if not audio_file.exists():
        raise FileNotFoundError(
            f"Expected audio file not found at {audio_file}. "
            "yt-dlp may have saved with a different name."
        )

    logger.info(f"Audio saved to: {audio_file}")
    return str(audio_file)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python youtube_loader.py <YOUTUBE_URL>")
        sys.exit(1)
    path = download_audio(sys.argv[1])
    print(f"Downloaded: {path}")
