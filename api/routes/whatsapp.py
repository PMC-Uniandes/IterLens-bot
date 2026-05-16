"""WhatsApp webhook handler."""

import logging
import time
import re

from fastapi import APIRouter, Request

from constants import OLD_MESSAGE_THRESHOLD_SECONDS, SUPERVISOR_WHATSAPP
from integrations.whatsapp.client import send_whatsapp_message
from integrations.whatsapp.parser import AUDIO_FAILED_MARKER, extract_whatsapp_message
from services.graph_runner import invoke_graph
from services.supabase import actualizar_status_reporte, get_reportes_pendientes
from src.config import llm, supervisor_llm
from src.graph import build_graph

logger = logging.getLogger(__name__)

router = APIRouter()
_graph = None

SUPERVISOR_HELP = (
    "\U0001F477 Opciones para supervisor:\n\n"
    "- APROBAR # (ej: APROBAR 123)\n"
    "- RECHAZAR # (ej: RECHAZAR 123)\n"
    "- LISTA (ver pendientes)"
)


def _normalize_phone(number: str) -> str:
    """Remove +, spaces, and @s.whatsapp.net suffix for comparison."""
    return re.sub(r"[+\s@]|s\.whatsapp\.net", "", number).strip()


def get_graph():
    """Get or create the compiled graph (lazy singleton)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def handle_supervisor_message(text: str, sender: str) -> dict:
    """Process supervisor messages: approve, reject, or list pending reports."""
    logger.info("Processing supervisor message: %s", text)

    try:
        parsed = supervisor_llm.invoke(text)
    except Exception:
        parsed = None

    if parsed and parsed.accion:
        accion = parsed.accion.strip().lower()
        ticket_id = parsed.id_ticket.strip() if parsed.id_ticket else None
    else:
        prompt = f"""
        Eres un asistente que interpreta mensajes de un supervisor de mantenimiento.

        ACCIONES:
        - aprobar: el supervisor quiere APROBAR un reporte.
        - rechazar: el supervisor quiere RECHAZAR un reporte.
        - listar: el supervisor quiere VER los reportes pendientes.

        Mensaje: "{text}"

        Responde SOLO con: accion|ticket_id  (ej: "aprobar|123" o "listar|" o "rechazar|456")
        Si no hay ticket: "aprobar|" o "rechazar|"
        Si no se entiende: "otro|"
        """
        try:
            response = llm.invoke(prompt)
            parts = response.content.strip().split("|")
            accion = parts[0].strip().lower() if len(parts) > 0 else "otro"
            ticket_id = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        except Exception:
            accion = "otro"
            ticket_id = None

    if accion == "listar":
        pendientes = get_reportes_pendientes()
        if not pendientes:
            await send_whatsapp_message(sender, "\u2705 No hay reportes pendientes de aprobaci\u00f3n.")
        else:
            msg_lines = ["\U0001F4CB Reportes pendientes:\n"]
            for r in pendientes:
                msg_lines.append(
                    f"#{r['id_registro_parada']} \u2014 M\u00e1q: {r.get('id_maquina')} | "
                    f"Falla: {r.get('id_tipo_parada')} | "
                    f"Turno: {r.get('turno')}"
                )
            msg_lines.append(f"\n{SUPERVISOR_HELP}")
            await send_whatsapp_message(sender, "\n".join(msg_lines))
        return {"status": "ok"}

    if accion in ("aprobar", "rechazar"):
        if not ticket_id or not ticket_id.isdigit():
            await send_whatsapp_message(
                sender,
                f"\u2753 \u00bfQu\u00e9 n\u00famero de ticket quieres {accion}?\n"
                f"Ej: {accion.upper()} 123\n"
                "Usa LISTA para ver los pendientes."
            )
            return {"status": "ok"}

        nuevo_status = "approved" if accion == "aprobar" else "rejected"
        actualizado = actualizar_status_reporte(int(ticket_id), nuevo_status)

        if not actualizado:
            await send_whatsapp_message(
                sender,
                f"\u274C No encontr\u00e9 el ticket #{ticket_id} o ya fue procesado."
            )
        else:
            emoji = "\u2705" if accion == "aprobar" else "\u274C"
            await send_whatsapp_message(
                sender,
                f"{emoji} Ticket #{ticket_id} ha sido {accion}do."
            )
        return {"status": "ok"}

    # No es una acción de supervisor — rutea al grafo para greeting/fallback
    logger.info("Supervisor message not an action, routing to graph")
    user_id = sender.split("@")[0]
    try:
        result = invoke_graph(get_graph(), text, user_id, user_id)
        reply = result["messages"][-1].content
        await send_whatsapp_message(sender, reply)
    except Exception:
        logger.exception("Graph invocation failed for supervisor")
        await send_whatsapp_message(sender, SUPERVISOR_HELP)
    return {"status": "ok"}


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Handle incoming WhatsApp webhook events via Evolution API."""
    try:
        body = await request.json()
    except Exception:
        logger.warning("Invalid JSON in WhatsApp webhook")
        return {"status": "error", "error": "invalid json"}

    logger.info("Incoming WhatsApp event: %s", body.get("event", "unknown"))

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

    if text == AUDIO_FAILED_MARKER:
        logger.warning("Audio transcription failed, sending fallback to %s", sender)
        fallback_msg = "Lo siento, en este momento no puedo procesar audios. \u00bfPodr\u00edas enviarlo en texto? \U0001F64F"
        try:
            await send_whatsapp_message(sender, fallback_msg)
        except Exception:
            logger.exception("Failed to send audio fallback message")
        return {"status": "ok", "reason": "audio_fallback_sent"}

    if not text:
        logger.info("No extractable text in message from %s", sender)
        return {"status": "ignored", "reason": "no text"}

    sender_clean = sender.split("@")[0]

    # Normalize both sides: Evolution API sends "573143721947" (no +),
    # while env var may be configured as "+571234567890"
    if SUPERVISOR_WHATSAPP and _normalize_phone(sender_clean) == _normalize_phone(SUPERVISOR_WHATSAPP):
        logger.info("Supervisor message detected from %s", sender)
        return await handle_supervisor_message(text, sender)

    # Operator flow
    logger.info("Received text from %s: %s", sender, text)

    user_id = sender_clean

    try:
        result = invoke_graph(get_graph(), text, user_id, user_id)
    except Exception:
        logger.exception("Graph invocation failed for WhatsApp user %s", user_id)
        return {"status": "error", "reason": "graph failure"}

    reply = result["messages"][-1].content

    try:
        await send_whatsapp_message(sender, reply)
    except Exception:
        logger.exception("Failed to send WhatsApp reply to %s", sender)
        return {"status": "error", "reason": "send failure"}

    # Send supervisor notification if the report was submitted for approval
    supervisor_msg = result.get("pending_supervisor_msg")
    if supervisor_msg and SUPERVISOR_WHATSAPP:
        try:
            await send_whatsapp_message(SUPERVISOR_WHATSAPP, supervisor_msg)
        except Exception:
            logger.exception("Failed to send supervisor notification")

    return {"status": "ok"}
