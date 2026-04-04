import os
from pathlib import Path
from tools.gemini_tools import GeminiTools
from tools.spacetime_tools import SpacetimeTools
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

gemini = GeminiTools()
st = SpacetimeTools()

def diagnose_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)

    # HEURISTIC: Skip LLM reasoning if it's a known simple case (saves time/tokens)
    logs = state.get("raw_logs", "")
    snapshot = str(state.get("system_snapshot", ""))
    
    pm2_logs_empty = len(logs.strip()) < 150 or "No process found" in logs
    
    # Check pm2_status from snapshot (injected by get_system_snapshot)
    pm2_status = str(state.get("system_snapshot", {}).get("pm2_status", ""))
    pm2_online = "online" in pm2_status.lower()

    # If PM2 doesn't show the app as online AND no real app logs came in
    # → safe to assume BOOT_FAILURE without relying on systemd markers
    no_process_running = not pm2_online

    if pm2_logs_empty and no_process_running:
        project_root = os.getenv("PROJECT_ROOT", "/root/app")
        app_name = os.path.basename(project_root.rstrip("/")) or "app"
        
        diagnosis = {
            "error_type": "BOOT_FAILURE",
            "root_cause": "The application is not running. Process missing and no logs found.",
            "severity": "high",
            "actions": [
                {
                    "action": "list_directory",
                    "target": project_root,
                    "reason": "Check if package.json and run scripts exist",
                    "risk_level": "low",
                    "reversible": True
                },
                {
                    "action": "read_file",
                    "target": project_root + "/package.json",
                    "reason": "Verify entry point and start script",
                    "risk_level": "low",
                    "reversible": True
                },
                {
                    "action": "pm2_start",
                    "target": "npm",
                    "params": {"name": app_name, "args": "-- start"},
                    "reason": "Start the application via pm2 using npm start script",
                    "risk_level": "low",
                    "reversible": True
                }
            ]
        }

        # ── Emit: fast-path diagnosis ──────────────────────────────────
        #print("DIAGNOSIS_READY", incident_id, diagnosis)
        st.emit("DIAGNOSIS_READY", incident_id, {
            "project_id": project_id,
            "error_type": diagnosis["error_type"],
            "root_cause": diagnosis["root_cause"],
            "fast_path": True,
        }, project_id=project_id)

        # ── Domain table: record AI decision ──────────────────────────
        st.add_ai_decision(
            project_id=project_id,
            incident_id=incident_id,
            error_type=diagnosis["error_type"],
            root_cause=diagnosis["root_cause"],
            severity=diagnosis["severity"],
            num_actions=len(diagnosis["actions"]),
        )

        return {**state, "project_id": project_id, "diagnosis": diagnosis}

    # WOW FACTOR: get the reasoning text, emit ONE event with the full content
    reasoning_text = gemini.stream_diagnose(
        logs=state["raw_logs"],
        snapshot=state["system_snapshot"],
        on_token=lambda chunk: None  # collect silently — no per-word HTTP calls
    )

    # Emit a single AGENT_THINKING event with the full reasoning
    st.emit("AGENT_THINKING", incident_id, {
        "project_id": project_id,
        "reasoning": reasoning_text[:500] if reasoning_text else "",
    }, project_id=project_id)


    # then get the structured diagnosis
    diagnosis = gemini.diagnose(
        logs=state["raw_logs"],
        snapshot=state["system_snapshot"],
        configs=state["config_files"]
    )

    # ── Emit: full diagnosis ready ─────────────────────────────────────
    # print("DIAGNOSIS_READY" , incident_id , {
    #     "project_id": project_id,
    #     "error_type": diagnosis.get("error_type", ""),
    #     "root_cause": diagnosis.get("root_cause", ""),
    #     "severity": diagnosis.get("severity", ""),
    #     "num_actions": len(diagnosis.get("actions", [])),
    # })
    st.emit("DIAGNOSIS_READY", incident_id, {
        "project_id": project_id,
        "error_type": diagnosis.get("error_type", ""),
        "root_cause": diagnosis.get("root_cause", ""),
        "severity": diagnosis.get("severity", ""),
        "num_actions": len(diagnosis.get("actions", [])),
    }, project_id=project_id)

    # ── Domain table: record AI decision ──────────────────────────────
    st.add_ai_decision(
        project_id=project_id,
        incident_id=incident_id,
        error_type=diagnosis.get("error_type", ""),
        root_cause=diagnosis.get("root_cause", ""),
        severity=diagnosis.get("severity", ""),
        num_actions=len(diagnosis.get("actions", [])),
    )

    return {**state, "project_id": project_id, "diagnosis": diagnosis}
