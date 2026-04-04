import os
from pathlib import Path
from dotenv import load_dotenv
from tools.vm_tools import VMTools
from tools.code_tools import CodeTools
from tools.gemini_tools import GeminiTools
from nodes.utils.state_helpers import (
    get_allowed_intents,
    build_execution_summary,
    track_action_set,
)
from utils.logger import (
    log_action_executed,
    log_action_failed,
    log_incident_resolved,
    log_rollback,
)
from utils.project_tree  import tree_cache
from utils.telemetry     import telemetry
from tools.ssh_utils     import sftp_write

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

vm     = VMTools()
code   = CodeTools(vm)
gemini = GeminiTools()

_REACTIVE_ENABLED = os.getenv("AGENT_REACTIVE_DECISIONS", "true").lower() == "true"

# Actions that change the remote filesystem — invalidate tree cache after these
_FILE_MUTATING_ACTIONS = {
    "write_file", "create_model_file", "rename_file",
    "patch_code_file", "fix_import_path", "fix_missing_module",
    "install_modules", "build_app", "install_dependency",
}


def execute_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)
    execution_results = []
    all_success = True

    if not _execute_enabled():
        summary = build_execution_summary(state, [])
        summary["skipped_execute"] = True
        summary["summary"] = (
            f"{summary['summary']} (Execute skipped: AGENT_EXECUTE_ACTIONS=false)"
        )
        # print("INCIDENT_RESOLVED" , incident_id, {
        #     "project_id": project_id,
        #     "skipped_execute": True,
        #     **summary,
        # })
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
            "execution_context": {},
            "incident_resolved": False,
            "summary_data":      summary,
            "final_summary":     summary["summary"],
        }

    allowed_intents = get_allowed_intents(state)

    for idx, intent in enumerate(allowed_intents):
        action = intent["action"]
        target = intent["target"]
        params = intent.get("params", {})

        # ── Reactive gate: ask Gemini if we should still run this ────
        # Skip if: first action (no context yet), OR last action (nothing after to skip/modify)
        is_first = idx == 0
        is_last  = idx == len(allowed_intents) - 1
        if _REACTIVE_ENABLED and not is_first and not is_last and execution_context:
            prev        = execution_results[-1]
            prev_action = prev.get("action", "previous_action")
            prev_output = str(prev.get("output", ""))[:1500]

            decision = gemini.decide_next_action(
                completed_action=prev_action,
                action_output=prev_output,
                next_action=action,
                next_target=target,
            )

            d      = decision.get("decision", "PROCEED")
            reason = decision.get("reason", "")

            if d == "SKIP":
                print(f"  ⏭️  SKIPPED  {action:<22} ← {reason}")
                execution_results.append({
                    "intent_id": intent["intent_id"],
                    "action":    action,
                    "status":    "SKIPPED",
                    "reason":    reason,
                })
                continue

            if d == "MODIFY":
                new_target = decision.get("modified_target") or target
                new_params = decision.get("modified_params") or params
                print(f"  ✏️  MODIFIED  {action:<22} target: {target} → {new_target}  ← {reason}")
                target = new_target
                params = new_params

        # ── Dispatch action ──────────────────────────────────────────
        try:
            output = _dispatch_with_code_tools(action, target, params)
            output["intent_id"] = intent["intent_id"]
            output.setdefault("status", "SUCCESS")

            log_action_executed(
                incident_id,
                action=action,
                target=target,
                status=output["status"],
                output=str(output.get("output", "")),
                intent_id=intent["intent_id"],
            )
            output["intent_id"] = result["intent_id"]
            output["status"] = output.get("status", "SUCCESS")
            # print("ACTION_EXECUTED" , incident_id, {
            #     "project_id": project_id,
            #     **output,
            # })
            st.emit("ACTION_EXECUTED", incident_id, {
                "project_id": project_id,
                **output,
            }, project_id=project_id)

            # ── Domain table: record execution ─────────────────────────
            st.record_execution(
                project_id=project_id,
                incident_id=incident_id,
                intent_id=result["intent_id"],
                action=intent["action"],
                status="success",
                output=str(output.get("output", "")),
            )

            execution_results.append(output)
            execution_context[action] = str(output.get("output", ""))[:1000]

            # Invalidate project tree cache if this action changed the filesystem
            if action in _FILE_MUTATING_ACTIONS and output["status"] == "SUCCESS":
                tree_cache.invalidate()

            if output["status"] != "SUCCESS":
                all_success = False

        except Exception as e:
            all_success = False
            failed = {
                "intent_id": result["intent_id"],
                "action": intent["action"],
                "status": "FAILED",
                "error": str(e)
            }
            # print('ACTION_FAILED' , incident_id, {
            #     "project_id": project_id,
            #     **failed,
            # })
            st.emit("ACTION_FAILED", incident_id, {
                "project_id": project_id,
                **failed,
            }, project_id=project_id)

            # ── Domain table: record failed execution ──────────────────
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

    # print("INCIDENT_RESOLVED" ,incident_id, {
    #     "project_id": project_id,
    #     **summary,
    # } )
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
    blocked = [r for r in state["enforcement_results"] if r["decision"] == "BLOCKED"]
    allowed = [r for r in state["enforcement_results"] if r["decision"] == "ALLOWED"]
    succeeded = [r for r in execution_results if r.get("status") in ("SUCCESS", "success")]

def _do_rollback(incident_id: str, file_snapshots: dict) -> bool:
    """Restore all snapshotted files to their pre-patch content via SFTP."""
    success_count = 0
    details       = []
    for file_path, original_content in file_snapshots.items():
        if not original_content:
            details.append(f"  ⚠️  {file_path}: empty snapshot — skipped")
            continue
        result = sftp_write(vm.client, file_path, original_content)
        if result.get("status") == "SUCCESS":
            success_count += 1
            details.append(f"  ✅ Restored: {file_path}")
        else:
            details.append(f"  ❌ Restore FAILED: {file_path}")
    log_rollback(incident_id, success_count, len(file_snapshots), details)
    return success_count > 0


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH — routes to vm_tools or code_tools depending on action
# ══════════════════════════════════════════════════════════════════════════════

def _dispatch_with_code_tools(action: str, target: str, params: dict) -> dict:
    """Extended dispatch that handles code-aware actions in addition to vm_tools."""

    # ── Code-aware actions (handled by CodeTools) ────────────────────
    if action == "patch_code_file":
        file_content = code.read_with_lines(target)
        error_ctx    = params.get("error_context", "Fix runtime/syntax error")
        patch_dict   = gemini.generate_code_patch(error_ctx, target, file_content)
        if not patch_dict.get("hunks"):
            return {"action": action, "target": target, "status": "FAILED", "output": "Gemini returned no hunks"}
        from models.patch import FilePatch, PatchHunk
        patch = FilePatch(
            file_path=patch_dict["file_path"],
            description=patch_dict.get("description", ""),
            confidence=patch_dict.get("confidence", 1.0),
            hunks=[PatchHunk(**h) for h in patch_dict["hunks"]],
        )
        result = code.apply_patch(patch)
        return {"action": action, "target": target, "status": result.status, "output": "\n".join(result.details)}

    if action == "read_file_with_lines":
        out = code.read_with_lines(target)
        return {"action": action, "target": target, "status": "SUCCESS", "output": out}

    if action == "grep_in_file":
        pattern = params.get("pattern", "")
        out = code.grep_in_file(target, pattern)
        return {"action": action, "target": target, "status": "SUCCESS", "output": out}

    if action == "grep_in_project":
        pattern = params.get("pattern", target)
        out = code.grep_in_project(pattern)
        return {"action": action, "target": target, "status": "SUCCESS", "output": out}

    if action == "inspect_db":
        db_type = params.get("db_type", "postgres")
        out = code.inspect_db_schema(db_type)
        return {"action": action, "target": target, "status": "SUCCESS", "output": out}

    if action == "db_query":
        sql     = params.get("sql", target)
        db_type = params.get("db_type", "postgres")
        out = code.run_safe_db_query(sql, db_type)
        return {"action": action, "target": target, "status": "SUCCESS", "output": out}

    # ── Standard VMTools dispatch ────────────────────────────────────
    return vm.dispatch(action, target, params)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _execute_enabled() -> bool:
    return os.getenv("AGENT_EXECUTE_ACTIONS", "true").lower() == "true"
