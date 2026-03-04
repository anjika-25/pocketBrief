"""
Text-to-Speech using Edge TTS (Microsoft Azure voices).
Fast, free, natural-sounding cloud TTS.
"""

import asyncio
import logging
import os
import platform
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RESPONSE_AUDIO_FILE, TTS_VOICE, AUDIO_DIR

import edge_tts

logger = logging.getLogger(__name__)


async def speak_async(text: str, output_path: str | None = None) -> str:
    """
    Async TTS — use directly in FastAPI async endpoints.

    Args:
        text: Text to synthesize.
        output_path: Where to save the MP3. Defaults to config RESPONSE_AUDIO_FILE.

    Returns:
        Path to the generated MP3 file.
    """
    output_path = output_path or str(RESPONSE_AUDIO_FILE)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Synthesizing {len(text)} characters with Edge TTS ({TTS_VOICE})…")
    communicate = edge_tts.Communicate(text, voice=TTS_VOICE)
    await communicate.save(output_path)
    logger.info(f"Audio saved to: {output_path}")

    return output_path


def speak(text: str, output_path: str | None = None, auto_play: bool = False) -> str:
    """
    Sync TTS wrapper — for standalone / non-async usage.

    Args:
        text: Text to synthesize.
        output_path: Where to save the MP3. Defaults to config RESPONSE_AUDIO_FILE.
        auto_play: Whether to open the audio file after generation.

    Returns:
        Path to the generated MP3 file.
    """
    output_path = output_path or str(RESPONSE_AUDIO_FILE)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    async def _gen():
        communicate = edge_tts.Communicate(text, voice=TTS_VOICE)
        await communicate.save(output_path)

    asyncio.run(_gen())
    logger.info(f"Audio saved to: {output_path}")

    if auto_play:
        _play_audio(output_path)

    return output_path


def _play_audio(path: str) -> None:
    """Open audio with the OS default application."""
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        logger.error(f"Failed to play audio: {e}")


if __name__ == "__main__":
    speak("Hello! I am your lecture assistant. How can I help you today?", auto_play=True)
