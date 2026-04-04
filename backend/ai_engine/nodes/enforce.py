from models.intent import Intent
from tools.armor_tools import ArmorTools
from tools.spacetime_tools import SpacetimeTools
from utils.logger import log_action_allowed, log_action_blocked

armor = ArmorTools()
st    = SpacetimeTools()


def enforce_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    results = []

    for intent_dict in state["intent_plan"]:
        intent = Intent(**intent_dict)
        result = armor.check_intent(intent)

        if result.decision == "BLOCKED":
            log_action_blocked(
                incident_id,
                intent_id=result.intent_id,
                action=result.action,
                policy=result.policy_matched,
                reason=result.reason,
            )
        else:
            log_action_allowed(
                incident_id,
                intent_id=result.intent_id,
                action=result.action,
                policy=result.policy_matched,
            )

        results.append(result.dict())

    return {**state, "enforcement_results": results}
