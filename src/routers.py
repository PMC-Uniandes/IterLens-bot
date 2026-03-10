from .state import ReportState
from langgraph.graph import END

def intent_router(state: ReportState):
    intent = state['intent']

    valid_intents = {"saludo", "reportar_falla", "completar_reporte", "listar_maquinas", "listar_tipos_parada", "confirmar", "cancelar"}

    if intent in valid_intents:
        return intent
    
    return END


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