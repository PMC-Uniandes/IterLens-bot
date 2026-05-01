"""Conditional routing functions for the LangGraph workflow."""

from langgraph.graph import END

from src.state import ReportState


def intent_router(state: ReportState) -> str:
    """Route to the appropriate node based on the classified intent.

    Args:
        state: The current ReportState with the 'intent' field set.

    Returns:
        The name of the next node to execute.
    """
    routes = {
        "saludo": "greeting",
        "reportar_falla": "report",
        "completar_reporte": "report",
        "confirmar": "confirm_node",
        "listar_maquinas": "list_machines",
        "listar_tipos_parada": "list_failures",
        "cancelar": "cancel_report",
        "otro": "fallback_node",
    }

    return routes.get(state.get("intent", ""), "fallback_node")


def route_after_validation(state: ReportState) -> str:
    """Route based on whether all required report fields are present.

    Args:
        state: The current ReportState with 'is_complete' field.

    Returns:
        'confirmar' if complete, otherwise END.
    """
    if state.get("is_complete"):
        return "confirmar"
    return "__end__"


def router_after_confirmation(state: ReportState) -> str:
    """Route based on the user's confirmation response.

    Args:
        state: The current ReportState with 'awaiting_confirmation' and 'confirmed' fields.

    Returns:
        'guardar' if confirmed, 'cancelar' if rejected, or END if still awaiting.
    """
    if state.get("awaiting_confirmation"):
        return "__end__"

    if state.get("confirmed"):
        return "guardar"
    return "cancelar"
