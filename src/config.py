from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langgraph.checkpoint.memory import MemorySaver
from .schema import ExtractionSchema, ConfirmationSchema
import os

load_dotenv()
memory = MemorySaver()

llm = ChatMistralAI(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-large-latest")

structured_llm = llm.with_structured_output(ExtractionSchema)
confirm_llm = llm.with_structured_output(ConfirmationSchema)


def get_graph_config(user_id: str) -> dict:
    """
    Thread_id único por operador. Sin esto, dos usuarios comparten estado.
    Usar el número de teléfono como user_id.
    """
    return {"configurable": {"thread_id": user_id}}