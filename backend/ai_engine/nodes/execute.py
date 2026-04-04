import os
from pathlib import Path
from dotenv import load_dotenv
from tools.vm_tools import VMTools
from tools.spacetime_tools import SpacetimeTools

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

vm = VMTools()
st = SpacetimeTools()


def _execute_enabled() -> bool:
    return os.getenv("AGENT_EXECUTE_ACTIONS", "true").lower() == "true"


def execute_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)
    execution_results = []
    all_success = True

    if not _execute_enabled():
        summary = build_summary(state, [])
        summary["skipped_execute"] = True
        summary["summary"] = (
            f"{summary['summary']} (Execute skipped: AGENT_EXECUTE_ACTIONS=false)"
        )
        st.emit("INCIDENT_RESOLVED", incident_id, {
            "project_id": project_id,
            "skipped_execute": True,
            **summary,
        }, project_id=project_id)
        st.resolve_incident(project_id=project_id, incident_id=incident_id)
        return {
            **state,
            "project_id": project_id,
            "execution_results": [],
            "incident_resolved": False,
            "summary_data": summary,
            "final_summary": summary["summary"],
        }

    for result in state["enforcement_results"]:
        if result["decision"] == "BLOCKED":
            continue  # ArmorClaw said no — skip entirely

        # find matching intent for params
        intent = next(
            (i for i in state["intent_plan"] if i["intent_id"] == result["intent_id"]),
            None
        )
        if not intent:
            continue

        try:
            output = vm.dispatch(
                action=intent["action"],
                target=intent["target"],
                params=intent.get("params", {})
            )
            output["intent_id"] = result["intent_id"]
            output["status"] = output.get("status", "SUCCESS")

            st.emit("ACTION_EXECUTED", incident_id, {
                "project_id": project_id,
                **output,
            }, project_id=project_id)

            st.record_execution(
                project_id=project_id,
                incident_id=incident_id,
                intent_id=result["intent_id"],
                action=intent["action"],
                status="success",
                output=str(output.get("output", "")),
            )

            execution_results.append(output)

        except Exception as e:
            all_success = False
            failed = {
                "intent_id": result["intent_id"],
                "action": intent["action"],
                "status": "FAILED",
                "error": str(e)
            }
            st.emit("ACTION_FAILED", incident_id, {
                "project_id": project_id,
                **failed,
            }, project_id=project_id)

            st.record_execution(
                project_id=project_id,
                incident_id=incident_id,
                intent_id=result["intent_id"],
                action=intent["action"],
                status="failed",
                output=str(e),
            )

            execution_results.append(failed)

    summary = build_summary(state, execution_results)

    st.emit("INCIDENT_RESOLVED", incident_id, {
        "project_id": project_id,
        **summary,
    }, project_id=project_id)
    st.resolve_incident(project_id=project_id, incident_id=incident_id)

    return {
        **state,
        "project_id": project_id,
        "execution_results": execution_results,
        "incident_resolved": all_success,
        "summary_data": summary,
        "final_summary": summary["summary"]
    }


def build_summary(state: dict, execution_results: list) -> dict:
    blocked   = [r for r in state["enforcement_results"] if r["decision"] == "BLOCKED"]
    allowed   = [r for r in state["enforcement_results"] if r["decision"] == "ALLOWED"]
    succeeded = [r for r in execution_results if r.get("status") in ("SUCCESS", "success")]

    return {
        "incident_id": state["incident_id"],
        "root_cause": state["diagnosis"].get("root_cause", ""),
        "severity": state["diagnosis"].get("severity", ""),
        "actions_allowed": len(allowed),
        "actions_blocked": len(blocked),
        "actions_succeeded": len(succeeded),
        "blocked_details": blocked,
        "summary": (
            f"{state['diagnosis'].get('affected_service', 'System')} incident resolved. "
            f"{len(succeeded)} fix(es) applied. "
            f"{len(blocked)} dangerous action(s) blocked by policy enforcement."
        )
    }
