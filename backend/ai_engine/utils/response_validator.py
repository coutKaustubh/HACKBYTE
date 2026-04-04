"""
utils/response_validator.py — Validate and sanitize Gemini diagnosis responses.

Problem: Gemini sometimes returns:
  - Unknown action names  ("restart_pm2" instead of "restart_service")
  - Paths not in project tree (hallucinated file locations)
  - Confidence outside 0–1 range
  - Missing required fields

This module runs AFTER Gemini responds and BEFORE the response enters the pipeline.
It doesn't re-call Gemini — it cleans what we got.

Design:
  HARD rules  → always enforced (unknown action → try alias → strip)
  SOFT rules  → warn but keep (file not in tree → flag, path still allowed)
  NO rules    → never enforce (reasoning text, confidence phrasing, etc.)

This keeps the agent flexible (handles novel situations) while preventing
known failure modes (wrong action names crash at dispatch).
"""

import os
from typing import Optional


# ── Canonical allowed action names ────────────────────────────────────────────

ALLOWED_ACTIONS: set[str] = {
    # Observation
    "read_logs", "read_file", "read_file_with_lines",
    "list_directory", "grep_in_file", "grep_in_project",
    "inspect_db", "db_query",
    # Code edits
    "patch_code_file", "write_file", "create_model_file",
    "fix_import_path", "fix_missing_module",
    # Build / deps
    "install_modules", "build_app", "install_dependency",
    # Process management
    "restart_service", "pm2_start", "kill_process",
    # Config / deploy
    "edit_config", "rename_file", "rollback_deploy", "redeploy_app",
}

# ── Near-miss alias map (common Gemini mistakes → correct name) ───────────────
# Keep this list short — only add when you observe a real hallucination.

ACTION_ALIASES: dict[str, Optional[str]] = {
    # PM2 variants
    "pm2_restart":       "restart_service",
    "restart_pm2":       "restart_service",
    "pm2_stop":          "restart_service",
    "pm2_reload":        "restart_service",
    "pm2_status":        "read_logs",          # agent can't query pm2 status as an action
    # npm variants
    "npm_install":       "install_modules",
    "install_packages":  "install_modules",
    "install_npm":       "install_modules",
    "run_npm_install":   "install_modules",
    "npm_build":         "build_app",
    "run_build":         "build_app",
    "npm_start":         "pm2_start",
    "start_app":         "pm2_start",
    # File variants
    "create_file":       "write_file",
    "overwrite_file":    "write_file",
    "read_log":          "read_logs",
    "cat_file":          "read_file",
    "ls_directory":      "list_directory",
    "list_files":        "list_directory",
    # Dangerous — map to None to signal "strip this silently"
    "delete_file":       None,
    "rm_file":           None,
    "remove_file":       None,
    "exec":              None,
    "exec_arbitrary":    None,
    "shell":             None,
    "run_command":       None,
    "drop_table":        None,   # handled by ArmorIQ too, but strip early
    "delete_database":   None,
}


# ── Main validator ────────────────────────────────────────────────────────────

def validate_diagnosis(diagnosis: dict, project_tree: str = "") -> dict:
    """
    Sanitize a Gemini diagnosis dict in-place (returns a cleaned copy).

    What it does:
      1. Ensure required top-level fields exist with sane defaults
      2. Clamp confidence to [0.0, 1.0]
      3. For each action:
           a. Alias-resolve unknown action names
           b. Strip actions that remain unknown after aliasing
           c. Soft-warn if target path is not in project tree (but keep it)
      4. Log every change so engineers can monitor prompt quality
    """
    result   = dict(diagnosis)
    warnings = []

    # ── 1. Required fields ────────────────────────────────────────────────────
    result.setdefault("error_type",       "UNKNOWN")
    result.setdefault("root_cause",       "Unknown — insufficient log data")
    result.setdefault("severity",         "medium")
    result.setdefault("confidence",       0.5)
    result.setdefault("affected_service", None)
    result.setdefault("actions",          [])
    result.setdefault("reasoning",        "")

    # ── 2. Clamp confidence ───────────────────────────────────────────────────
    try:
        conf = float(result["confidence"])
        result["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        result["confidence"] = 0.5
        warnings.append("confidence was non-numeric — defaulted to 0.5")

    # ── 3. Validate actions ───────────────────────────────────────────────────
    tree_paths   = set(project_tree.splitlines()) if project_tree else set()
    clean_actions = []

    for action_dict in result.get("actions", []):
        if not isinstance(action_dict, dict):
            warnings.append(f"Skipped non-dict action: {action_dict!r}")
            continue

        action_name = action_dict.get("action", "")
        target      = action_dict.get("target", "")

        # ── (a) Alias resolution ──────────────────────────────────────────
        if action_name not in ALLOWED_ACTIONS:
            alias = ACTION_ALIASES.get(action_name)
            if alias is None and action_name in ACTION_ALIASES:
                # Explicitly mapped to None → dangerous/forbidden
                warnings.append(f"STRIPPED dangerous action '{action_name}' (policy)")
                continue
            elif alias:
                warnings.append(f"Aliased '{action_name}' → '{alias}'")
                action_dict = dict(action_dict)
                action_dict["action"] = alias
                action_name = alias
            else:
                # Unknown and not in alias map → strip
                warnings.append(f"STRIPPED unknown action '{action_name}' (not in allowed list)")
                continue

        # ── (b) Soft path validation ──────────────────────────────────────
        # Only check file-targeting actions, not service/DB actions
        is_file_action = action_name in {
            "read_file", "read_file_with_lines", "write_file",
            "patch_code_file", "fix_import_path", "create_model_file",
            "rename_file", "grep_in_file",
        }
        if is_file_action and target and tree_paths and not target.startswith("/etc"):
            if target not in tree_paths:
                # Soft warn — don't strip. The file might be new or the tree might be stale.
                warnings.append(
                    f"⚠️  soft-warn: target '{target}' not in cached project tree "
                    f"(tree may be stale — action kept)"
                )

        # ── (c) Ensure essential fields ───────────────────────────────────
        action_dict.setdefault("reason",     "Suggested by Gemini diagnosis")
        action_dict.setdefault("risk_level", "medium")
        action_dict.setdefault("reversible", True)
        action_dict.setdefault("params",     {})

        clean_actions.append(action_dict)

    result["actions"] = clean_actions

    # ── 4. Surface warnings ───────────────────────────────────────────────────
    if warnings:
        result["_validation_warnings"] = warnings
        prefix = "  🔍 [validator]"
        for w in warnings:
            print(f"{prefix} {w}")

    return result


# ── Confidence auto-deflation ─────────────────────────────────────────────────

def adjust_confidence_for_log_quality(diagnosis: dict, raw_logs: str) -> dict:
    """
    Deflate Gemini's confidence if the evidence base is thin.

    Rules (soft, additive penalty):
      - Logs < 200 chars    → -0.25  (almost no data)
      - "No entries" in log → -0.20  (journalctl returned nothing)
      - error_type UNKNOWN  → -0.15  (Gemini didn't recognize it)
      - No actions proposed → -0.15  (Gemini couldn't prescribe anything)

    These penalties stack. The result is clamped to [0.05, 1.0].
    We never zero out confidence (Gemini might still be right).
    """
    conf    = float(diagnosis.get("confidence", 0.5))
    penalty = 0.0
    reasons = []

    log_len = len((raw_logs or "").strip())
    if log_len < 200:
        penalty += 0.25
        reasons.append(f"very short logs ({log_len} chars)")
    elif log_len < 800:
        penalty += 0.10
        reasons.append(f"thin logs ({log_len} chars)")

    if "No entries" in (raw_logs or ""):
        penalty += 0.20
        reasons.append("journalctl returned 'No entries'")

    if diagnosis.get("error_type") == "UNKNOWN":
        penalty += 0.15
        reasons.append("error_type=UNKNOWN")

    if not diagnosis.get("actions"):
        penalty += 0.15
        reasons.append("no actions proposed")

    if penalty > 0:
        adjusted = max(0.05, round(conf - penalty, 2))
        print(f"  🔍 [validator] Confidence adjusted {conf:.2f} → {adjusted:.2f} "
              f"(reasons: {', '.join(reasons)})")
        diagnosis = dict(diagnosis)
        diagnosis["confidence"] = adjusted
        diagnosis.setdefault("_confidence_adjusted", True)

    return diagnosis
