from langgraph.graph import StateGraph, START, END
from .routers import intent_router, route_after_validation, router_after_confirmation
from .nodes import (
    parse_intent, 
    greeting_handler, 
    report_handler, 
    mapper, 
    validator, 
    confirm, 
    list_machines, 
    list_failures,
    save_report,
    cancel_report,
    restart
)
from .state import ReportState
from .config import memory


def build_graph() -> StateGraph:
    # Crera un grafo con el esquema del estado como parámetro
    graph_builder = StateGraph(ReportState)

    # Agregar nodos
    graph_builder.add_node("parse_intent", parse_intent)
    graph_builder.add_node("greeting", greeting_handler)
    graph_builder.add_node("report", report_handler)
    graph_builder.add_node("mapper_node", mapper)
    graph_builder.add_node("validator_node", validator)
    graph_builder.add_node("confirm_node", confirm)
    graph_builder.add_node("list_machines", list_machines)
    graph_builder.add_node("list_failures", list_failures)
    graph_builder.add_node("save_report", save_report)
    graph_builder.add_node("cancel_report", cancel_report)
    graph_builder.add_node("restart_node", restart)


    # Agregar aristas
    graph_builder.add_edge("report", "mapper_node")
    graph_builder.add_edge("mapper_node", "validator_node")
    graph_builder.add_edge("save_report", "restart_node")
    graph_builder.add_edge("cancel_report", "restart_node")


    # Agregar aristas condicionales
    graph_builder.add_conditional_edges(
        "parse_intent",
        intent_router,
        {
            "saludo": "greeting",
            "reportar_falla": "report",
            "completar_reporte": "report",
            "confirmar": "confirm_node",
            "listar_maquinas": "list_machines",
            "listar_tipos_parada": "list_failures",
            "cancelar": "cancel_report",
            "__end__": END
        }
    )

    graph_builder.add_conditional_edges(
        "validator_node",
        route_after_validation,
        {
            "confirmar": "confirm_node",
            "__end__": END
        }
    )

    graph_builder.add_conditional_edges(
        "confirm_node",
        router_after_confirmation,
        {
            "guardar": "save_report",
            "cancelar": "cancel_report",
            "__end__": END
        }
    )
    

    # Crear inicio del grafo
    graph_builder.add_edge(START, "parse_intent")

    # Fin del grafo
    graph_builder.add_edge("restart_node", END)

    return graph_builder.compile(checkpointer=memory)
