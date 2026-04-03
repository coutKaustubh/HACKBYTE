from langgraph.graph import StateGraph, END
from nodes.collect import collect_node
from nodes.diagnose import diagnose_node
from nodes.plan import plan_node
from nodes.enforce import enforce_node
from nodes.execute import execute_node

def build_graph():
    graph = StateGraph(dict)

    graph.add_node("collect",  collect_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("plan",     plan_node)
    graph.add_node("enforce",  enforce_node)
    graph.add_node("execute",  execute_node)

    graph.set_entry_point("collect")
    graph.add_edge("collect",  "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_edge("plan",     "enforce")
    graph.add_edge("enforce",  "execute")
    graph.add_edge("execute",  END)

    return graph.compile()

agent = build_graph()
