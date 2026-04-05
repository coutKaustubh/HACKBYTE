from langgraph.graph import StateGraph, END
import asyncio

from nodes.collect  import collect_node
from nodes.diagnose import diagnose_node
from nodes.plan     import plan_node
from nodes.enforce  import enforce_node
from nodes.execute  import execute_node
from nodes.verify   import verify_node


# ── Human-readable node labels (shown in frontend terminal) ──────────────────
NODE_LABELS = {
    "collect":  "Collecting Logs",
    "diagnose": "AI Diagnosis",
    "plan":     "Planning Actions",
    "enforce":  "Enforcing Policies",
    "execute":  "Executing Actions",
    "verify":   "Verifying Resolution",
}


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


# ── Async streaming wrapper ───────────────────────────────────────────────────

async def stream_agent_events(initial_state: dict):
    """
    Async generator that wraps astream_events and yields clean JSON-serializable
    dicts for consumption by a Django Channels WebSocket consumer or SSE endpoint.

    Each yielded dict has the shape:
      { "event": str, "name": str, "data": any }

    Event types:
      "node_start"   — a pipeline node started
      "node_end"     — a pipeline node finished (includes partial output keys)
      "llm_token"    — a single LLM token streamed from the model
      "tool_start"   — a tool call started
      "tool_end"     — a tool call finished
      "done"         — the full pipeline finished (includes final state)
    """
    final_state = {}

    try:
        async for event in agent.astream_events(initial_state, version="v2"):
            kind   = event.get("event", "")
            name   = event.get("name",  "")
            data   = event.get("data",  {})

            # ── Node lifecycle ────────────────────────────────────────────────
            if kind == "on_chain_start" and name in NODE_LABELS:
                yield {
                    "event": "node_start",
                    "name":  name,
                    "label": NODE_LABELS.get(name, name),
                    "data":  {},
                }

            elif kind == "on_chain_end" and name in NODE_LABELS:
                output = data.get("output", {})
                # Only surface safe scalar/summary keys — avoid dumping raw_logs
                safe_keys = {
                    k: v for k, v in (output or {}).items()
                    if k in ("incident_id", "project_id", "diagnosis",
                              "intent_plan", "enforcement_results",
                              "execution_results", "incident_resolved",
                              "final_summary", "retries", "summary_data")
                }
                final_state.update(output or {})
                yield {
                    "event": "node_end",
                    "name":  name,
                    "label": NODE_LABELS.get(name, name),
                    "data":  safe_keys,
                }

                # ── Send full agent state snapshot to frontend ────────────────
                truncated_state = {}
                for k, v in final_state.items():
                    if isinstance(v, str) and len(v) > 300:
                        truncated_state[k] = v[:300] + "..."
                    else:
                        truncated_state[k] = v
                yield {
                    "event": "agent_state",
                    "name":  name,
                    "label": NODE_LABELS.get(name, name),
                    "data":  truncated_state,
                }

            # ── LLM token streaming ───────────────────────────────────────────
            elif kind == "on_chat_model_stream":
                chunk = data.get("chunk", {})
                # LangChain AIMessageChunk → .content is the token text
                token = getattr(chunk, "content", "") or ""
                if token:
                    yield {
                        "event": "llm_token",
                        "name":  name,
                        "data":  {"token": token},
                    }

            # ── Tool calls ───────────────────────────────────────────────────
            elif kind == "on_tool_start":
                yield {
                    "event": "tool_start",
                    "name":  name,
                    "data":  {"input": str(data.get("input", ""))[:200]},
                }

            elif kind == "on_tool_end":
                yield {
                    "event": "tool_end",
                    "name":  name,
                    "data":  {"output": str(data.get("output", ""))[:200]},
                }

    except Exception as e:
        yield {
            "event": "error",
            "name":  "pipeline",
            "data":  {"message": str(e)},
        }
        return

    # ── Terminal event ────────────────────────────────────────────────────────
    yield {
        "event": "done",
        "name":  "pipeline",
        "data": {
            "incident_id":       final_state.get("incident_id"),
            "incident_resolved": final_state.get("incident_resolved", False),
            "final_summary":     final_state.get("final_summary", ""),
            "retries":           final_state.get("retries", 0),
        },
    }
