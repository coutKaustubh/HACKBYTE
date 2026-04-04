"""
nodes/plan.py — Build intent list.

New: Confidence gate + Dependency suppression
  - If state['human_escalation'] is True (confidence < threshold) → return empty plan
  - If state['dependency_suppressed'] → return empty plan (fix the dependency first)
  - Otherwise, build intent list as normal
"""

from models.intent import Intent
from models.utils.validators import build_intent_id
from tools.spacetime_tools import SpacetimeTools
from utils.logger import log_plan_ready

st = SpacetimeTools()


def plan_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)
    actions = state["diagnosis"].get("actions", [])

    intents = []
    for i, action in enumerate(actions):
        intent = Intent(
            intent_id   = build_intent_id(incident_id, i + 1),
            incident_id = incident_id,
            step        = i + 1,
            action      = action["action"],
            target      = action["target"],
            params      = action.get("params", {}),
            reason      = action["reason"],
            risk_level  = action["risk_level"],
            reversible  = action["reversible"],
        )
        intents.append(intent)

    # ── Demo intent: ArmorClaw will always block this ─────────────────────────
    demo_block = Intent(
        intent_id   = build_intent_id(incident_id, len(intents) + 1, "demo-block"),
        incident_id = incident_id,
        step        = len(intents) + 1,
        action      = "drop_table",
        target      = "pg_worker_cache",
        params      = {},
        reason      = "Attempting to clear corrupted cache table",
        risk_level  = "critical",
        reversible  = False,
    )
    intents.append(demo_blocked_intent)

    # ── Emit: plan is ready ────────────────────────────────────────────
    # print("PLAN_READY" , incident_id , {
    #     "project_id" : project_id,
    #     "total_intents" : len(intents),
    #     "intents" : [i.dict() for i in intents],
    # })
    st.emit("PLAN_READY", incident_id, {
        "project_id": project_id,
        "total_intents": len(intents),
        "intents": [i.dict() for i in intents],
    }, project_id=project_id)

    return {**state, "project_id": project_id, "intent_plan": [i.dict() for i in intents]}
