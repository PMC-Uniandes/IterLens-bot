"""LangGraph state graph builder for the maintenance report workflow."""

from langgraph.graph import END, START, StateGraph

from src.config import memory
from src.nodes import (
    cancel_report,
    fallback,
    greeting_handler,
    list_failures,
    list_machines,
    mapper,
    parse_intent,
    report_handler,
    restart,
    submit_for_approval,
    validator,
)
from src.routers import (
    intent_router,
    route_after_validation,
)
from src.state import ReportState


def build_graph() -> StateGraph:
    """Build and compile the LangGraph state machine."""
    builder = StateGraph(ReportState)

    builder.add_node("parse_intent", parse_intent)
    builder.add_node("greeting", greeting_handler)
    builder.add_node("report", report_handler)
    builder.add_node("mapper_node", mapper)
    builder.add_node("validator_node", validator)
    builder.add_node("submit_for_approval", submit_for_approval)
    builder.add_node("list_machines", list_machines)
    builder.add_node("list_failures", list_failures)
    builder.add_node("cancel_report", cancel_report)
    builder.add_node("restart_node", restart)
    builder.add_node("fallback_node", fallback)

    builder.add_edge("report", "mapper_node")
    builder.add_edge("mapper_node", "validator_node")
    builder.add_edge("submit_for_approval", "restart_node")
    builder.add_edge("cancel_report", "restart_node")

    builder.add_conditional_edges("parse_intent", intent_router)

    builder.add_conditional_edges(
        "validator_node",
        route_after_validation,
        {"submit_approval": "submit_for_approval", "__end__": END},
    )

    builder.add_edge(START, "parse_intent")
    builder.add_edge("restart_node", END)

    return builder.compile(checkpointer=memory)
