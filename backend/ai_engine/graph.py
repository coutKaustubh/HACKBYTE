"""
graph.py — Non-linear LangGraph pipeline.

Old graph (linear):
    collect → diagnose → [code_fix?] → plan → enforce → execute → verify → [retry?]

New graph (non-linear, multi-branch):

    collect
      ↓
    triage ─── TRIVIAL  ─────────────────────────────────── plan ─┐
      │         (heuristic diagnosis, no Gemini)                   │
      COMPLEX                                                       │
      ↓                                                            │
    diagnose (Gemini deep analysis)                                │
      ↓                                                            │
    reflect (Gemini CoT self-critique)                             │
      ├── APPROVE/MODIFY ─── code_fix? ─── plan ──────────────────┤
      └── ESCALATE ──── END                                        │
                                                                   │
    escalate_node ─────────────────────────────────────── END      │
                                                                   │
    plan → enforce → execute → verify ─────────────────────────────┘
      │                            ↓
      │                    (not resolved)
      └──────────────── collect (retry, max 3 with dedup guard)

Key design decisions:
  - triage keeps Gemini tokens for truly ambiguous cases
  - reflect adds one short CoT critique pass (cheap, high value)
  - escalate_node is a proper named node so we can log + emit alert from it
  - routing.py::continue_or_end handles the retry loop (unchanged)
"""

from langgraph.graph import StateGraph, END

from nodes.collect  import collect_node
from nodes.triage   import triage_node, route_after_triage
from nodes.diagnose import diagnose_node
from nodes.reflect  import reflect_node, route_after_reflect
from nodes.code_fix import code_fix_node
from nodes.plan     import plan_node
from nodes.enforce  import enforce_node
from nodes.execute  import execute_node
from nodes.utils.routing import continue_or_end


# ── Escalate terminal node ─────────────────────────────────────────────────────

def escalate_node(state: dict) -> dict:
    """
    Terminal node for human escalation.
    Logs the situation and emits a SpacetimeDB event if available.
    """
    incident_id = state.get("incident_id", "unknown")
    reason      = state.get("reflect_reasoning") or "Low confidence diagnosis" 
    diagnosis   = state.get("diagnosis", {})

    print()
    print("═" * 64)
    print(f"🚨  ESCALATED TO HUMAN  {incident_id}")
    print(f"   Error   : {diagnosis.get('error_type', 'UNKNOWN')}")
    print(f"   Reason  : {reason[:120]}")
    print(f"   Confidence: {diagnosis.get('confidence', 0):.0%}")
    print(f"   → No automated actions will be taken.")
    print("═" * 64)
    print()

    return {**state, "incident_resolved": False, "human_escalation": True}


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(dict)

    # ── Register nodes ─────────────────────────────────────────────────────────
    graph.add_node("collect",  collect_node)
    graph.add_node("triage",   triage_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("reflect",  reflect_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("code_fix", code_fix_node)
    graph.add_node("plan",     plan_node)
    graph.add_node("enforce",  enforce_node)
    graph.add_node("execute",  execute_node)

    # ── Entry ──────────────────────────────────────────────────────────────────
    graph.set_entry_point("collect")
    graph.add_edge("collect", "triage")

    # ── Triage branch ──────────────────────────────────────────────────────────
    #   TRIVIAL  → skip Gemini, go straight to plan (diagnosis already set)
    #   COMPLEX  → full Gemini diagnosis
    #   ESCALATE → system unreachable, stop
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "trivial":  "plan",
            "complex":  "diagnose",
            "escalate": "escalate",
        },
    )

    # ── Diagnose → Reflect (always: reflect decides what to do next) ────────
    graph.add_edge("diagnose", "reflect")

    # ── Reflect branch ─────────────────────────────────────────────────────────
    #   APPROVE/MODIFY + code error  → code_fix
    #   APPROVE/MODIFY + other       → plan
    #   ESCALATE                     → escalate
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {
            "code_fix": "code_fix",
            "plan":     "plan",
            "escalate": "escalate",
        },
    )

    # ── Code fix → plan ────────────────────────────────────────────────────────
    graph.add_edge("code_fix", "plan")

    # ── Execution pipeline ───────────────────────────────────────────────────────────
    graph.add_edge("plan",    "enforce")
    graph.add_edge("enforce", "execute")

    # ── Escalate is terminal ─────────────────────────────────────────────────────────
    graph.add_edge("escalate", END)

    # ── Retry loop: execute → collect or END ──────────────────────────────────────
    graph.add_conditional_edges(
        "execute",
        continue_or_end,
        {"continue": "collect", "end": END},
    )

    return graph.compile()


agent = build_graph()
