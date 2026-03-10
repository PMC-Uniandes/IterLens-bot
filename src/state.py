from typing import Annotated, Optional, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ReportState(TypedDict):
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
    
    missing_fields: List[str]
    is_complete: bool
    awaiting_confirmation: bool
    confirmed: bool