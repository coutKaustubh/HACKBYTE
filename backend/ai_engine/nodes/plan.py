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

    # ── Confidence gate ────────────────────────────────────────────────────────
    if state.get("human_escalation"):
        print(f"  🚨 [plan] Human escalation active — no intent plan created. Skipping auto-fix.")
        return {**state, "intent_plan": []}

    # ── Dependency suppression gate ────────────────────────────────────────────
    if state.get("dependency_suppressed"):
        print(f"  🕸️  [plan] Dependency suppressed — no intent plan created. Fix dependencies first.")
        return {**state, "intent_plan": []}

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
    intents.append(demo_block)

    log_plan_ready(incident_id, [i.dict() for i in intents])
    return {**state, "intent_plan": [i.dict() for i in intents]}
