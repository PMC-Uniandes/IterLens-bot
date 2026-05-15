"""LLM configuration and LangGraph memory setup.

Initializes the Mistral AI chat model, structured output schemas,
and in-memory checkpoint storage for conversation state persistence.
"""

import logging
import os

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langgraph.checkpoint.memory import MemorySaver

from src.schema import ExtractionSchema, SupervisorActionSchema

load_dotenv()

logger = logging.getLogger(__name__)

memory = MemorySaver()

LLM_MODEL = os.getenv("LLM_MODEL", "mistral-large-latest")
llm = ChatMistralAI(api_key=os.getenv("MISTRAL_API_KEY"), model=LLM_MODEL)

structured_llm = llm.with_structured_output(ExtractionSchema)
supervisor_llm = llm.with_structured_output(SupervisorActionSchema)


def get_graph_config(user_id: str) -> dict:
    return {"configurable": {"thread_id": user_id}}
