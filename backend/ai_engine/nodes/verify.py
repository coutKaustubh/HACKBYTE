"""
nodes/verify.py — Post-execution verification + auto-rollback.

New: Rollback mechanism
  - If verification fails AND state['_file_snapshots'] exists (set by code_fix_node),
    all snapshotted files are restored to their pre-patch content via SFTP.
  - Rollback result is logged and stored in state['rollback_applied'].
  - Patch cache entries for rolled-back files are invalidated so next run
    gets a fresh Gemini patch rather than reusing the broken one.
"""
import time
from tools.vm_tools import VMTools
from tools.ssh_utils import sftp_write
from nodes.utils.state_helpers import track_action_set
from utils.logger import log_verify, log_rollback
from utils.telemetry import telemetry
from utils.cache import patch_cache, TTLCache

vm = VMTools()


def verify_node(state: dict) -> dict:
    incident_id = state.get("incident_id", "unknown")
    retries     = state.get("retries", 0)

    # Give PM2 time to fully boot the process
    time.sleep(8)

    # ── Primary check: PM2 online status ─────────────────────────────────────
    pm2_out    = vm._run("pm2 status --no-color 2>/dev/null")
    pm2_online = "online" in pm2_out.lower()

    # ── Secondary check: HTTP /health endpoint ────────────────────────────────
    health_ok = False
    try:
        import httpx
        if vm.app_url:
            resp = httpx.get(f"{vm.app_url}/health", timeout=8.0)
            health_ok = resp.status_code < 500
    except Exception:
        health_ok = False

    incident_resolved = pm2_online or health_ok

    log_verify(
        incident_id,
        pass_num=retries + 1,
        resolved=incident_resolved,
        pm2_out=pm2_out if not incident_resolved else "",
    )

    # ── Telemetry: mark resolved if we're done ────────────────────────────────
    if incident_resolved:
        telemetry.mark_resolved(incident_id)

    # ── Rollback: restore snapshotted files if patch didn't help ──────────────
    rollback_applied = False
    file_snapshots   = state.get("_file_snapshots", {})

    if not incident_resolved and file_snapshots and state.get("code_patch_applied"):
        rollback_applied = _do_rollback(incident_id, file_snapshots)
        if rollback_applied:
            # Clear patch cache for rolled-back files so next run tries fresh patch
            for file_path in file_snapshots:
                # Invalidate any cache entries associated with this file
                patch_cache.clear()   # safest: clear all patch entries after bad patch
                break

    # ── Track action sets for dedup guard ────────────────────────────────────
    exec_results  = state.get("execution_results", [])
    prev_attempts = track_action_set(state, exec_results)

    return {
        **state,
        "incident_resolved": incident_resolved,
        "retries":           retries + 1,
        "_prev_action_sets": prev_attempts,
        "rollback_applied":  rollback_applied,
    }


# ── Rollback helper ────────────────────────────────────────────────────────────

def _do_rollback(incident_id: str, file_snapshots: dict) -> bool:
    """
    Restore all snapshotted files to their pre-patch content via SFTP.
    Returns True if at least one file was successfully restored.
    """
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
            details.append(f"  ❌ Restore FAILED: {file_path} — {result.get('output')}")

    log_rollback(incident_id, success_count, len(file_snapshots), details)
    return success_count > 0
