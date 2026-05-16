"""Conditional routing functions for the LangGraph workflow."""

from langgraph.graph import END

from src.state import ReportState


def intent_router(state: ReportState) -> str:
    """Route to the appropriate node based on the classified intent."""
    routes = {
        "saludo": "greeting",
        "reportar_falla": "report",
        "completar_reporte": "report",
        "listar_maquinas": "list_machines",
        "listar_tipos_parada": "list_failures",
        "seleccionar_opcion": "handle_selection",
        "cancelar": "cancel_report",
        "otro": "fallback_node",
    }

    return routes.get(state.get("intent", ""), "fallback_node")


def route_after_validation(state: ReportState) -> str:
    """Route to submit_for_approval if complete, otherwise END."""
    if state.get("is_complete"):
        return "submit_approval"
    return "__end__"
