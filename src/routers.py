from .state import ReportState
from langgraph.graph import END

def intent_router(state: ReportState):
    routes = {
        "saludo":               "greeting",
        "reportar_falla":       "report",
        "completar_reporte":    "report",
        "confirmar":            "confirm_node",
        "listar_maquinas":      "list_machines",
        "listar_tipos_parada":  "list_failures",
        "cancelar":             "cancel_report",
        "otro":                 "fallback_node",
        "__end__":              END
    }

    return routes.get(state.get("intent"), "fallback_node")


def route_after_validation(state: ReportState):
    if state["is_complete"]:
        return "confirmar"
    else:
        return END
    

def router_after_confirmation(state: ReportState):
    if state["awaiting_confirmation"]:
        return END
    else:
        if state["confirmed"]:
            return "guardar"
        else:
            return "cancelar"