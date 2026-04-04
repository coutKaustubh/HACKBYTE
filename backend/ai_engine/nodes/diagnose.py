import os

from tools.gemini_tools import GeminiTools
from tools.spacetime_tools import SpacetimeTools
from dotenv import load_dotenv
import os 

load_dotenv()

gemini = GeminiTools()
st = SpacetimeTools()

def diagnose_node(state: dict) -> dict:
    incident_id = state["incident_id"]

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
        
        # Smart detection: check if this is an npm project (Next.js, Express, etc)
        # Use 'npm -- start' via pm2 instead of a bare index.js
        app_name = os.path.basename(project_root.rstrip("/")) or "app"
        
        diagnosis = {
            "error_type": "BOOT_FAILURE",
            "root_cause": "The application is not running. Process missing and no logs found.",
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
                    # npm -- start works for Next.js, CRA, Express etc. without needing index.js
                    "target": "npm",
                    "params": {"name": app_name, "args": "-- start"},
                    "reason": "Start the application via pm2 using npm start script",
                    "risk_level": "low",
                    "reversible": True
                }
            ]
        }
        print("DIAGNOSIS_READY", incident_id, diagnosis)
        return {**state, "diagnosis": diagnosis}

    # WOW FACTOR: stream reasoning tokens to SpacetimeDB live
    reasoning_chunks = []
    def on_token(chunk):
        reasoning_chunks.append(chunk)
        print("AGENT_THINKING", incident_id, {"chunk": chunk})

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

    print("DIAGNOSIS_READY", incident_id, diagnosis)

    return {**state, "diagnosis": diagnosis}
