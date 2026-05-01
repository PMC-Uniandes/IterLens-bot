"""Shared service for invoking the LangGraph agent."""

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def invoke_graph(graph, text: str, user_id: str, thread_id: str) -> str:
    """Invoke the LangGraph agent and return the assistant's reply.

    Args:
        graph: The compiled LangGraph instance.
        text: The user's message text.
        user_id: Unique identifier for the user.
        thread_id: Conversation thread identifier for state persistence.

    Returns:
        The last assistant message content from the graph execution.

    Raises:
        Exception: Propagates any graph execution errors.
    """
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=text)],
            "user_id": user_id,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content
