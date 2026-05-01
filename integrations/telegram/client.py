"""Telegram API client for sending messages."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


async def send_message(chat_id: int, text: str, reply_to: int | None = None) -> None:
    """Send a text message to a Telegram chat.

    Args:
        chat_id: The Telegram chat identifier.
        text: The message text to send.
        reply_to: Optional message ID to reply to.
    """
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        if response.status_code != 200:
            logger.error("Failed to send Telegram message: %s", response.text)
