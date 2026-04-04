"""
nodes/code_fix.py — Responsive code editing node.

New: Rollback mechanism
  - Before applying any patch, the original file content is snapshot'd into
    state['_file_snapshots'] = {file_path: original_content}
  - verify.py reads this and auto-restores files if verification still fails
    after patching, protecting the VM from broken patches stuck in place.
"""

from tools.vm_tools    import VMTools
from tools.code_tools  import CodeTools
from tools.gemini_tools import GeminiTools
from models.patch      import FilePatch, PatchHunk
from utils.logger      import log_build_hook
from utils.cache       import patch_cache, TTLCache

import os

vm     = VMTools()
code   = CodeTools(vm)
gemini = GeminiTools()

CODE_ERROR_TYPES = {
    "MODULE_NOT_FOUND",
    "SYNTAX_ERROR",
    "RUNTIME_ERROR",
    "IMPORT_ERROR",
    "ENV_MISSING",
}


def code_fix_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    diagnosis   = state.get("diagnosis", {})
    error_type  = diagnosis.get("error_type", "UNKNOWN")

    # ── Only engage for code-level errors ─────────────────────────────────────
    if error_type not in CODE_ERROR_TYPES:
        return {**state, "code_patch_applied": None}

    # ── Skip if low-confidence diagnosis escalated to human ───────────────────
    if state.get("human_escalation"):
        _log(incident_id, "⏭️  Skipping code fix — low-confidence diagnosis escalated to human")
        return {**state, "code_patch_applied": None}

    target_file = _resolve_target_file(diagnosis)
    if not target_file:
        _log(incident_id, "⚠️  No target file identified — skipping code fix")
        return {**state, "code_patch_applied": None}

    _log(incident_id, f"📄 Reading file: {target_file}")
    file_content = code.read_with_lines(target_file, max_lines=400)

    if "[CodeTools] File not found" in file_content:
        _log(incident_id, f"❌ File not found: {target_file}")
        return {**state, "code_patch_applied": None}

    # ── SNAPSHOT original content before patching (enables rollback) ──────────
    raw_original = vm._run(f"cat {target_file} 2>&1")
    file_snapshots = dict(state.get("_file_snapshots", {}))
    if target_file not in file_snapshots:
        file_snapshots[target_file] = raw_original
        _log(incident_id, f"📸 Snapshot saved for {target_file} ({len(raw_original)} chars)")

    error_context = (
        f"Error type: {error_type}\n"
        f"Root cause: {diagnosis.get('root_cause', '')}\n"
        f"Reasoning: {diagnosis.get('reasoning', '')}\n"
        f"PM2 / App logs:\n{state.get('raw_logs', '')[:2000]}"
    )

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = TTLCache.make_key(target_file, file_content, error_context)
    cached    = patch_cache.get(cache_key)

    if cached is not None:
        _log(incident_id, f"💾 Cache HIT — reusing patch. (stats: {patch_cache.stats()})")
        patch_dict = cached
    else:
        _log(incident_id, f"🤖 Cache MISS — asking Gemini. (stats: {patch_cache.stats()})")
        # Wire incident_id for cost tracking
        gemini.incident_id = incident_id
        patch_dict = gemini.generate_code_patch(
            error_context=error_context,
            file_path=target_file,
            file_content_with_lines=file_content,
            project_tree=state.get("project_tree", ""),
        )
        if patch_dict.get("hunks"):
            patch_cache.set(cache_key, patch_dict)

    if not patch_dict.get("hunks"):
        _log(incident_id, "⚠️  Gemini returned no hunks — no patch applied")
        return {**state, "code_patch_applied": None, "_file_snapshots": file_snapshots}

    try:
        patch = FilePatch(
            file_path=patch_dict["file_path"],
            description=patch_dict.get("description", ""),
            confidence=patch_dict.get("confidence", 1.0),
            hunks=[PatchHunk(**h) for h in patch_dict["hunks"]],
        )
    except Exception as e:
        _log(incident_id, f"❌ Patch model validation failed: {e}")
        return {**state, "code_patch_applied": None, "_file_snapshots": file_snapshots}

    _log(incident_id, f"🔧 Applying {len(patch.hunks)} hunk(s) to {patch.file_path}...")
    result = code.apply_patch(patch)

    for detail in result.details:
        _log(incident_id, detail)

    if result.status == "FAILED":
        _log(incident_id, f"❌ Patch FAILED — invalidating cache")
        patch_cache.invalidate(cache_key)
    else:
        _log(incident_id, f"✅ Patch {result.status}: {result.hunks_applied} hunk(s) applied")

    return {
        **state,
        "code_patch_applied": result.dict(),
        "_file_snapshots":    file_snapshots,    # carries snapshots for potential rollback
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_target_file(diagnosis: dict) -> str | None:
    if diagnosis.get("resolved_absolute"):
        return diagnosis["resolved_absolute"]
    for action in diagnosis.get("actions", []):
        if action.get("action") in ("write_file", "patch_code_file", "fix_import_path", "create_model_file"):
            return action.get("target")
    if diagnosis.get("missing_path"):
        return diagnosis["missing_path"]
    for action in diagnosis.get("actions", []):
        if action.get("action") == "read_file":
            return action.get("target")
    return None


def should_run_code_fix(state: dict) -> str:
    error_type = state.get("diagnosis", {}).get("error_type", "UNKNOWN")
    # Also skip code fix if dependency suppressed
    if state.get("dependency_suppressed"):
        return "plan"
    return "code_fix" if error_type in CODE_ERROR_TYPES else "plan"


def _log(incident_id: str, msg: str):
    log_build_hook(f"[code_fix/{incident_id}]", msg)
