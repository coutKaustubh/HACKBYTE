from models.intent import Intent
from tools.armor_tools import ArmorTools
from tools.spacetime_tools import SpacetimeTools

armor = ArmorTools()
st = SpacetimeTools()

def enforce_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    results = []

    for intent_dict in state["intent_plan"]:
        intent = Intent(**intent_dict)
        result = armor.check_intent(intent)

        if result.decision == "BLOCKED":
            # THIS IS THE DEMO MOMENT
            # Divyansh flashes red, Sharad triggers ElevenLabs voice
            st.emit("ACTION_BLOCKED", incident_id, {
                "intent_id": result.intent_id,
                "action": result.action,
                "policy": result.policy_matched,
                "reason": result.reason,
                # this field tells ElevenLabs what to speak
                "speak": f"Action {result.action} was blocked. Reason: {result.reason}"
            })
        else:
            st.emit("ACTION_ALLOWED", incident_id, {
                "intent_id": result.intent_id,
                "action": result.action,
                "policy": result.policy_matched
            })

        results.append(result.dict())

    return {**state, "enforcement_results": results}
