"""
nodes/execute.py — Reactive execution node.

Instead of blindly executing a fixed plan, each action's output is:
  1. Logged and stored in execution_context
  2. Sent to Gemini: "given this output, should the NEXT action PROCEED / SKIP / MODIFY?"
  3. The next action is adjusted accordingly before execution

This makes the agent truly responsive — it reads its own outputs and adapts.

State helpers live in nodes/utils/state_helpers.py.
Code-tool dispatch lives in tools/dispatch.py (via vm_tools.dispatch).
"""

import os
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

load_dotenv()

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
    incident_id        = state["incident_id"]
    execution_results: list[dict] = []
    execution_context: dict = {}     # maps action_name → output (for reactive decisions)
    all_success        = True

    if not _execute_enabled():
        summary = build_execution_summary(state, [])
        summary["skipped_execute"] = True
        summary["summary"] += " (Execute skipped: AGENT_EXECUTE_ACTIONS=false)"
        log_incident_resolved(incident_id, summary)
        return {
            **state,
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

            execution_results.append(output)
            execution_context[action] = str(output.get("output", ""))[:1000]

            # Invalidate project tree cache if this action changed the filesystem
            if action in _FILE_MUTATING_ACTIONS and output["status"] == "SUCCESS":
                tree_cache.invalidate()

            if output["status"] != "SUCCESS":
                all_success = False

        except Exception as e:
            all_success = False
            log_action_failed(incident_id, action=action, intent_id=intent["intent_id"], error=str(e))
            execution_results.append({
                "intent_id": intent["intent_id"],
                "action":    action,
                "status":    "FAILED",
                "error":     str(e),
            })
            execution_context[action] = f"ERROR: {e}"

    summary = build_execution_summary(state, execution_results)
    log_incident_resolved(incident_id, summary)

    # ── Rollback: if any file was patched and all_success is False, restore snapshots ─
    rollback_applied = False
    file_snapshots = state.get("_file_snapshots", {})
    if not all_success and file_snapshots and state.get("code_patch_applied"):
        rollback_applied = _do_rollback(incident_id, file_snapshots)
        if rollback_applied:
            from utils.cache import patch_cache
            patch_cache.clear()   # stale patch — force fresh Gemini on next run

    # ── Telemetry ─────────────────────────────────────────────────────────────
    if all_success:
        telemetry.mark_resolved(incident_id)

    return {
        **state,
        "execution_results":  execution_results,
        "execution_context":  execution_context,
        "incident_resolved":  all_success,
        "_prev_action_sets":  track_action_set(state, execution_results),
        "rollback_applied":   rollback_applied,
        "summary_data":       summary,
        "final_summary":      summary["summary"],
        "retries":            state.get("retries", 0) + 1,
    }


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
