"""ElevenLabs speech-to-text service."""

import logging
import os
from io import BytesIO

from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)

ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "scribe_v2")

_client = None


def _get_client() -> ElevenLabs:
    """Return a lazily initialized ElevenLabs client."""
    global _client
    if _client is None:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.error("ELEVENLABS_API_KEY not configured")
            raise ValueError("ElevenLabs API key not configured")
        _client = ElevenLabs(api_key=api_key)
    return _client


async def transcribe_audio(audio_bytes: bytes, language: str = "spa") -> str:
    """Transcribe audio bytes to text using ElevenLabs Scribe.

    Args:
        audio_bytes: The raw audio data.
        language: The language code for transcription (default: Spanish).

    Returns:
        The transcribed text, or empty string on failure.
    """
    try:
        client = _get_client()
        transcription = client.speech_to_text.convert(
            file=("audio.ogg", BytesIO(audio_bytes)),
            model_id=ELEVENLABS_MODEL,
            language_code=language,
            tag_audio_events=False,
            diarize=False,
        )
        return transcription.text
    except Exception:
        logger.exception("Failed to transcribe audio")
        return ""
