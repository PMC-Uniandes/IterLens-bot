"""WhatsApp webhook handler."""

import logging
import time

from fastapi import APIRouter, Request

from src.graph import build_graph
from integrations.whatsapp.parser import extract_whatsapp_message
from integrations.whatsapp.client import send_whatsapp_message
from services.graph_runner import invoke_graph
from constants import OLD_MESSAGE_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)

router = APIRouter()
_graph = None


def get_graph():
    """Get or create the compiled graph (lazy singleton)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Handle incoming WhatsApp webhook events via Evolution API.

    Validates the payload structure, filters stale/group/self messages,
    invokes the LangGraph agent, and sends the reply.
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Invalid JSON in WhatsApp webhook")
        return {"status": "error", "error": "invalid json"}

    logger.info("Incoming WhatsApp event: %s", body.get("event", "unknown"))
    logger.info("Webhook body keys: %s", list(body.keys()))

    data = body.get("data", {})
    message_data = data.get("message", {})
    logger.info("Message data keys: %s", list(message_data.keys()))

    # Log if audio is present (without logging full URL for security)
    audio_msg = message_data.get("audioMessage", {})
    if audio_msg:
        logger.info("audioMessage found with keys: %s", list(audio_msg.keys()))
        logger.info("audioMessage URL present: %s", bool(audio_msg.get("url")))
        logger.info("audioMessage mimetype: %s", audio_msg.get("mimetype"))
        logger.info("audioMessage has mediaKey: %s", bool(audio_msg.get("mediaKey")))

    data = body.get("data", {})
    key = data.get("key", {})
    sender = key.get("remoteJid", "")

    if key.get("fromMe"):
        logger.info("Ignoring own message from %s", sender)
        return {"status": "ignored", "reason": "fromMe"}

    if body.get("event") != "messages.upsert":
        logger.info("Ignoring non-messages.upsert event: %s", body.get("event"))
        return {"status": "ignored", "reason": "wrong event"}

    if "@g.us" in sender:
        logger.info("Ignoring group message from %s", sender)
        return {"status": "ignored", "reason": "group"}

    now = int(time.time())
    msg_time = data.get("messageTimestamp", 0)
    age = now - msg_time

    if age > OLD_MESSAGE_THRESHOLD_SECONDS:
        logger.info("Ignoring stale message (%ds old)", age)
        return {"status": "ignored", "reason": "old message"}

    text = await extract_whatsapp_message(data)
    if not text:
        logger.info("No extractable text in message from %s", sender)
        return {"status": "ignored", "reason": "no text"}

    logger.info("Received text from %s: %s", sender, text)

    user_id = sender.split("@")[0]

    try:
        reply = invoke_graph(get_graph(), text, user_id, user_id)
    except Exception:
        logger.exception("Graph invocation failed for WhatsApp user %s", user_id)
        return {"status": "error", "reason": "graph failure"}

    try:
        await send_whatsapp_message(sender, reply)
    except Exception:
        logger.exception("Failed to send WhatsApp reply to %s", sender)
        return {"status": "error", "reason": "send failure"}

    return {"status": "ok"}
