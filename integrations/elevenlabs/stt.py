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
    if not audio_bytes:
        logger.error("transcribe_audio called with empty audio_bytes")
        return ""

    logger.info("Transcribing audio: %d bytes", len(audio_bytes))

    # Save debug file if audio is small enough
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_bytes)
            logger.info("Saved debug audio to: %s", f.name)
    except Exception as e:
        logger.warning("Could not save debug audio: %s", e)

    try:
        client = _get_client()

        # Detect audio format based on header bytes
        # WhatsApp typically sends: audio/ogg (Opus in OGG container)
        # ElevenLabs supports: ogg, mp3, wav, flac, m4a, mp4, webm
        if audio_bytes[:4] == b'RIFF':
            ext = "wav"
        elif audio_bytes[:4] == b'OggS':
            # Check if it's OGG - could be .ogg or .oga, ElevenLabs accepts .ogg
            ext = "ogg"
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
            ext = "mp3"
        elif audio_bytes[:4] == b'fLaC':
            ext = "flac"
        else:
            ext = "ogg"  # Default for WhatsApp
            logger.warning("Unknown audio format header: %s, using .ogg", audio_bytes[:8].hex())

        # Validate minimum size (at least 1KB for valid audio)
        if len(audio_bytes) < 1024:
            logger.error("Audio too small (%d bytes), likely corrupted", len(audio_bytes))
            return ""

        logger.info("Sending audio to ElevenLabs with extension: %s", ext)

        transcription = client.speech_to_text.convert(
            file=(f"audio.{ext}", BytesIO(audio_bytes)),
            model_id=ELEVENLABS_MODEL,
            language_code=language,
            tag_audio_events=False,
            diarize=False,
        )
        logger.info("Transcription successful: %s", transcription.text[:100] if transcription.text else "")
        return transcription.text
    except Exception as e:
        logger.exception("Failed to transcribe audio: %s", e)
        return ""
