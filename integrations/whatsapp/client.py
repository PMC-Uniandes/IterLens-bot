"""WhatsApp API client for sending messages via Evolution API."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "lensbot-whatsapp")


async def send_whatsapp_message(to: str, text: str) -> None:
    """Send a text message via the Evolution API WhatsApp instance.

    Args:
        to: The recipient's phone number.
        text: The message text to send.
    """
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": to, "text": text}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error("Failed to send WhatsApp message: %s", response.text)
