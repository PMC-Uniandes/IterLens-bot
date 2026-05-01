"""Test endpoint for webhook simulation."""

import logging

from fastapi import APIRouter

from src.graph import build_graph
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


@router.post("/webhook/test")
async def test_webhook(from_number: str, body: str) -> dict:
    """Test endpoint to invoke the graph directly.

    Args:
        from_number: The sender's phone number (used as user/thread ID).
        body: The message text to process.

    Returns:
        A dict with the 'reply' field containing the agent's response.
    """
    try:
        reply = invoke_graph(get_graph(), body, from_number, from_number)
    except Exception:
        logger.exception("Graph invocation failed in test endpoint")
        return {"reply": None, "error": "graph failure"}

    return {"reply": reply}
