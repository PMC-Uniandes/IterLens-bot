"""WhatsApp message parsing utilities."""

import httpx

from integrations.elevenlabs.stt import transcribe_audio


async def extract_whatsapp_message(data: dict) -> str | None:
    """Extract text content from a WhatsApp message payload.

    Handles text messages and audio messages (via ElevenLabs transcription).

    Args:
        data: The message data dictionary from Evolution API.

    Returns:
        The extracted text, or None if no text/audio could be parsed.
    """
    message_data = data.get("message", {})

    text = (
        message_data.get("conversation")
        or message_data.get("extendedTextMessage", {}).get("text")
    )

    if not text:
        audio = message_data.get("audioMessage")
        if audio:
            audio_bytes = await _download_audio_async(audio.get("url"))
            if audio_bytes:
                return await transcribe_audio(audio_bytes)

    return text


async def _download_audio_async(url: str | None) -> bytes | None:
    """Download audio bytes from a URL asynchronously.

    Args:
        url: The audio file URL.

    Returns:
        The audio bytes, or None if download failed.
    """
    if not url:
        return None

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            return res.content if res.status_code == 200 else None
    except Exception:
        return None
