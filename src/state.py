"""TypedDict schema for the maintenance report LangGraph state.

Defines all fields that can be read/written by nodes in the workflow,
including user context, conversation messages, intent classification,
report field data, and flow control flags.
"""

from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ReportState(TypedDict):
    """State shared across all nodes in the maintenance report workflow.

    Attributes:
        user_id: Unique identifier for the user (phone number or Telegram ID).
        messages: Conversation history with automatic message aggregation.
        intent: The classified intent from the latest user message.
        tipo_parada_texto: Raw text description of the failure type.
        maquina_texto: Raw text description of the machine.
        id_maquina: Database ID for the matched machine.
        id_tipo_parada: Database ID for the matched failure type.
        turno: The shift when the failure occurred (dia/tarde/noche).
        tiempo_parada_horas: Duration of the machine downtime in hours.
        prioridad: Severity level of the incident (alta/media/baja).
        observaciones: Additional notes from the operator.
        missing_fields: List of required fields not yet collected.
        is_complete: Whether all required fields have been gathered.
        awaiting_confirmation: Whether the bot is waiting for report confirmation.
        confirmed: The user's confirmation decision (True/False).
    """

    user_id: str

    messages: Annotated[list, add_messages]
    intent: Optional[str]

    tipo_parada_texto: Optional[str]
    maquina_texto: Optional[str]

    id_maquina: Optional[str]
    id_tipo_parada: Optional[str]
    turno: Optional[str]
    tiempo_parada_horas: Optional[str]
    prioridad: Optional[str]
    observaciones: Optional[str]

    missing_fields: list[str]
    is_complete: bool
    awaiting_confirmation: bool
    confirmed: bool
