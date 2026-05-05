"""WhatsApp message parsing utilities."""

import httpx
import logging

from integrations.elevenlabs.stt import transcribe_audio

logger = logging.getLogger(__name__)


async def extract_whatsapp_message(data: dict) -> str | None:
    """Extract text content from a WhatsApp message payload.

    Handles text messages and audio messages (via ElevenLabs transcription).

    Args:
        data: The message data dictionary from Evolution API.

    Returns:
        The extracted text, or None if no text/audio could be parsed.
    """
    message_data = data.get("message", {})

    logger.info("Message data keys: %s", list(message_data.keys()))

    text = (
        message_data.get("conversation")
        or message_data.get("extendedTextMessage", {}).get("text")
    )

    if not text:
        audio = message_data.get("audioMessage")
        if audio:
            logger.info("Audio message detected. Keys: %s", list(audio.keys()))
            logger.info("Audio URL present: %s", bool(audio.get("url")))
            logger.info("Audio mimetype: %s", audio.get("mimetype"))
            logger.info("Audio has mediaKey: %s", bool(audio.get("mediaKey")))

            audio_bytes = await _download_audio_via_evolution(data)
            if audio_bytes:
                logger.info("Audio downloaded: %d bytes", len(audio_bytes))
                return await transcribe_audio(audio_bytes)
            else:
                logger.error("Failed to download audio via Evolution API")
        else:
            logger.info("No audioMessage found in message_data")

    return text


async def _download_audio_via_evolution(data: dict) -> bytes | None:
    """Download audio using Evolution API's getBase64 endpoint.

    This properly handles WhatsApp's encrypted audio by letting Evolution API
    decrypt and return the audio as base64.

    Args:
        data: The full message data from webhook (data field).

    Returns:
        The audio bytes, or None if failed.
    """
    import os
    import base64

    api_key = os.getenv("EVOLUTION_API_KEY", "")
    api_url = os.getenv("EVOLUTION_API_URL", "")
    instance = os.getenv("EVOLUTION_INSTANCE", "")

    if not all([api_key, api_url, instance]):
        logger.error("Missing Evolution API configuration for audio download")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{api_url}/chat/getBase64FromMediaMessage/{instance}"
            headers = {"apikey": api_key, "Content-Type": "application/json"}

            # Extract message key for the getBase64 endpoint
            key = data.get("key", {})
            payload = {
                "message": {"key": {"id": key.get("id")}},
                "convertToMp4": False
            }

            logger.info("Requesting base64 from Evolution API for msg ID: %s", key.get("id"))
            res = await client.post(url, json=payload, headers=headers)

            if res.status_code not in (200, 201):
                logger.error("Evolution API getBase64 failed: %d - %s", res.status_code, res.text[:300])
                return None

            logger.info("Evolution API getBase64 success: HTTP %d", res.status_code)

            result = res.json()
            logger.info("getBase64 response keys: %s", list(result.keys()) if isinstance(result, dict) else "not dict")

            # Handle different response formats
            base64_data = None
            if isinstance(result, dict):
                base64_data = result.get("base64") or result.get("data") or result.get("audio")

            if not base64_data:
                logger.error("No base64 data in response: %s", str(result)[:200])
                return None

            # Handle data URL format: "data:audio/ogg;base64,..."
            if isinstance(base64_data, str) and "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]

            if isinstance(base64_data, str):
                audio_bytes = base64.b64decode(base64_data)
            else:
                logger.error("base64_data is not a string: %s", type(base64_data))
                return None

            logger.info("Decoded audio from Evolution API: %d bytes", len(audio_bytes))

            # Validate it's not an error response (like JSON in the audio)
            if audio_bytes[:1] == b'{':
                logger.error("Audio bytes start with '{' - likely an error response, not audio")
                return None

            return audio_bytes

    except Exception as e:
        logger.exception("Failed to get audio via Evolution API: %s", e)
        return None


async def _download_audio_async(url: str | None) -> bytes | None:
    """Download audio bytes from a URL asynchronously.

    Args:
        url: The audio file URL.

    Returns:
        The audio bytes, or None if download failed.
    """
    if not url:
        return None

    import os
    api_key = os.getenv("EVOLUTION_API_KEY", "")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"apikey": api_key} if api_key else {}
            res = await client.get(url, headers=headers)
            if res.status_code != 200:
                logger.error("Failed to download audio: HTTP %d - %s", res.status_code, res.text[:200])
                return None
            content = res.content
            logger.info("Downloaded audio: %d bytes from %s", len(content), url[:50])
            return content
    except Exception as e:
        logger.exception("Exception downloading audio: %s", e)
        return None
