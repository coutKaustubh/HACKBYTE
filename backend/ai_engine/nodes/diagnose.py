from tools.gemini_tools import GeminiTools
from tools.spacetime_tools import SpacetimeTools

gemini = GeminiTools()
st = SpacetimeTools()

def diagnose_node(state: dict) -> dict:
    incident_id = state["incident_id"]

    # WOW FACTOR: stream reasoning tokens to SpacetimeDB live
    reasoning_chunks = []
    def on_token(chunk):
        reasoning_chunks.append(chunk)
        st.emit("AGENT_THINKING", incident_id, {"chunk": chunk})

    # stream the thinking first (wow factor)
    gemini.stream_diagnose(
        logs=state["raw_logs"],
        snapshot=state["system_snapshot"],
        on_token=on_token
    )

    # then get the structured diagnosis
    diagnosis = gemini.diagnose(
        logs=state["raw_logs"],
        snapshot=state["system_snapshot"],
        configs=state["config_files"]
    )

    st.emit("DIAGNOSIS_READY", incident_id, diagnosis)

    return {**state, "diagnosis": diagnosis}
