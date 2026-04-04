from models.intent import Intent
from tools.spacetime_tools import SpacetimeTools

st = SpacetimeTools()

def plan_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    actions = state["diagnosis"].get("actions", [])

    intents = []
    for i, action in enumerate(actions):
        intent = Intent(
            intent_id=f"int-{incident_id}-{i+1:03d}",
            incident_id=incident_id,
            step=i + 1,
            action=action["action"],
            target=action["target"],
            params=action.get("params", {}),
            reason=action["reason"],
            risk_level=action["risk_level"],
            reversible=action["reversible"]
        )
        intents.append(intent)

    # ADD ONE DANGEROUS INTENT FOR DEMO — ArmorClaw will block this
    demo_blocked_intent = Intent(
        intent_id=f"int-{incident_id}-demo-block",
        incident_id=incident_id,
        step=len(intents) + 1,
        action="drop_table",           # always blocked by P-001
        target="pg_worker_cache",
        params={},
        reason="Attempting to clear corrupted cache table",
        risk_level="critical",
        reversible=False
    )
    intents.append(demo_blocked_intent)

    print("PLAN_READY", incident_id, {
        "total_intents": len(intents),
        "intents": [i.dict() for i in intents]
    })

    return {**state, "intent_plan": [i.dict() for i in intents]}
