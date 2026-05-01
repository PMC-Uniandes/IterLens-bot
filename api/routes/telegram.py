"""Telegram webhook handler."""

import logging
import os

from fastapi import APIRouter, Request

from src.graph import build_graph
from integrations.telegram.parser import (
    build_thread_id,
    extract_message_data,
    is_bot_mentioned,
)
from integrations.telegram.client import send_message
from services.graph_runner import invoke_graph

logger = logging.getLogger(__name__)

router = APIRouter()
_graph = None


def get_graph():
    """Get or create the compiled graph (lazy singleton)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Handle incoming Telegram webhook events.

    Extracts message data, invokes the LangGraph agent, and sends the reply.
    In groups, only responds if the bot is mentioned or replied to.
    """
    try:
        update = await request.json()
    except Exception:
        logger.warning("Invalid JSON in Telegram webhook")
        return {"ok": False, "error": "invalid json"}

    extracted = await extract_message_data(update)
    if not extracted:
        return {"ok": True}

    chat_id, message_id, user_id, text = extracted

    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
    if not is_bot_mentioned(update, bot_username):
        return {"ok": True}

    thread_id = build_thread_id(update, user_id)

    try:
        reply_text = invoke_graph(get_graph(), text, user_id, thread_id)
    except Exception:
        logger.exception("Graph invocation failed for Telegram user %s", user_id)
        return {"ok": False, "error": "graph error"}

    message = update.get("message") or update.get("edited_message")
    chat_type = message["chat"]["type"]
    reply_to = message_id if chat_type != "private" else None

    try:
        await send_message(chat_id, reply_text, reply_to=reply_to)
    except Exception:
        logger.exception("Failed to send Telegram reply to chat %s", chat_id)

    return {"ok": True}
