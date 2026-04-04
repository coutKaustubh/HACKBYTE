from models.intent import Intent
from tools.armor_tools import ArmorTools
from tools.spacetime_tools import SpacetimeTools
from utils.logger import log_action_allowed, log_action_blocked

armor = ArmorTools()
st    = SpacetimeTools()


def enforce_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)
    results = []

    for intent_dict in state["intent_plan"]:
        intent = Intent(**intent_dict)
        result = armor.check_intent(intent)

        if result.decision == "BLOCKED":
            # THIS IS THE DEMO MOMENT
            # Divyansh flashes red, Sharad triggers ElevenLabs voice
            print("ACTION_BLOCKED" , incident_id, {
                "project_id": project_id,
                "intent_id": result.intent_id,
                "action": result.action,
                "policy": result.policy_matched,
                "reason": result.reason,
                # this field tells ElevenLabs what to speak
                "speak": f"Action {result.action} was blocked. Reason: {result.reason}"} )
            st.emit("ACTION_BLOCKED", incident_id, {
                "project_id": project_id,
                "intent_id": result.intent_id,
                "action": result.action,
                "policy": result.policy_matched,
                "reason": result.reason,
                # this field tells ElevenLabs what to speak
                "speak": f"Action {result.action} was blocked. Reason: {result.reason}",
            }, project_id=project_id)
        else:
            # print("ACTION_ALLOWED" ,  incident_id, {
            #     "project_id": project_id,
            #     "intent_id": result.intent_id,
            #     "action": result.action,
            #     "policy": result.policy_matched,
            # })
            st.emit("ACTION_ALLOWED", incident_id, {
                "project_id": project_id,
                "intent_id": result.intent_id,
                "action": result.action,
                "policy": result.policy_matched,
            }, project_id=project_id)

        # ── Domain table: record safety check verdict ──────────────────
        st.add_safety_check(
            project_id=project_id,
            incident_id=incident_id,
            intent_id=result.intent_id,
            action=result.action,
            allowed=(result.decision == "ALLOWED"),
            policy=result.policy_matched or "",
            reason=result.reason or "",
        )

        results.append(result.dict())

    return {**state, "project_id": project_id, "enforcement_results": results}
