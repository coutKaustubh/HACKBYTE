from langgraph.graph import StateGraph, END

from nodes.collect  import collect_node
from nodes.diagnose import diagnose_node
from nodes.plan     import plan_node
from nodes.enforce  import enforce_node
from nodes.execute  import execute_node
from nodes.verify   import verify_node


def _continue_or_end(state: dict) -> str:
    """After verify: retry up to 3 times if not resolved, then end."""
    if state.get("incident_resolved"):
        return "end"
    if state.get("retries", 0) >= 3:
        return "end"
    return "continue"


def build_graph():
    graph = StateGraph(dict)

    graph.add_node("collect",  collect_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("plan",     plan_node)
    graph.add_node("enforce",  enforce_node)
    graph.add_node("execute",  execute_node)
    graph.add_node("verify",   verify_node)

    graph.set_entry_point("collect")
    graph.add_edge("collect",  "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_edge("plan",     "enforce")
    graph.add_edge("enforce",  "execute")
    graph.add_edge("execute",  "verify")

    graph.add_conditional_edges(
        "verify",
        _continue_or_end,
        {"continue": "collect", "end": END},
    )

    return graph.compile()


agent = build_graph()
