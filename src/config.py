"""LLM configuration and LangGraph memory setup.

Initializes the Mistral AI chat model, structured output schemas,
and in-memory checkpoint storage for conversation state persistence.
"""

import logging
import os

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langgraph.checkpoint.memory import MemorySaver

from src.schema import ConfirmationSchema, ExtractionSchema

load_dotenv()

logger = logging.getLogger(__name__)

memory = MemorySaver()

LLM_MODEL = os.getenv("LLM_MODEL", "mistral-large-latest")
llm = ChatMistralAI(api_key=os.getenv("MISTRAL_API_KEY"), model=LLM_MODEL)

structured_llm = llm.with_structured_output(ExtractionSchema)
confirm_llm = llm.with_structured_output(ConfirmationSchema)


def get_graph_config(user_id: str) -> dict:
    """Generate the LangGraph configuration for a given user.

    Creates a unique thread_id per operator to isolate conversation state.
    Without this, two users would share the same state.

    Args:
        user_id: The user's phone number or Telegram ID.

    Returns:
        A configuration dict suitable for graph.invoke() calls.
    """
    return {"configurable": {"thread_id": user_id}}
