"""
nodes/triage.py — Fast heuristic pre-classification (NO Gemini call).

Problem with the old graph: every incident went straight to Gemini diagnose,
wasting tokens on obvious cases like "PM2 has no process" (BOOT_FAILURE).

Triage answers one question fast:
  "Is this TRIVIAL enough to skip Gemini, or COMPLEX enough to need it?"

Outputs (sets state['triage_result']):
  "trivial"    → diagnosis already set by heuristics, skip to plan
  "complex"    → needs Gemini deep diagnosis
  "escalate"   → system completely unresponsive, can't safely diagnose

This saves Gemini API calls for the most common incident type (BOOT_FAILURE)
and gives the agent sub-second response for obvious failures.
"""

import os
import re


# ── Known log patterns → instant classification ────────────────────────────────
_PATTERN_MAP = [
    # MODULE_NOT_FOUND
    (re.compile(r"Cannot find module '([^']+)'", re.I),  "MODULE_NOT_FOUND", "medium"),
    (re.compile(r"Error: Cannot find module", re.I),      "MODULE_NOT_FOUND", "medium"),
    # SYNTAX_ERROR
    (re.compile(r"SyntaxError:", re.I),                   "SYNTAX_ERROR",    "high"),
    # PORT_IN_USE
    (re.compile(r"EADDRINUSE|address already in use", re.I), "PORT_IN_USE",  "high"),
    # ENV_MISSING
    (re.compile(r"(NEXT_PUBLIC_|DATABASE_URL|SECRET_KEY)[^\s]* is not defined", re.I), "ENV_MISSING", "medium"),
    # OOM / memory
    (re.compile(r"ENOMEM|JavaScript heap out of memory", re.I), "RUNTIME_ERROR", "critical"),
    # DB connection
    (re.compile(r"ECONNREFUSED.*:5432|connection to server.*failed|FATAL:.*password", re.I), "DB_CONNECTION_ERROR", "high"),
]

_MODULE_RE = re.compile(r"Cannot find module '([^']+)'", re.I)


def triage_node(state: dict) -> dict:
    logs        = state.get("raw_logs", "")
    snapshot    = state.get("system_snapshot", {})
    incident_id = state["incident_id"]
    project_root = os.getenv("PROJECT_ROOT", "/root/app")
    app_name     = os.path.basename(project_root.rstrip("/")) or "app"

    pm2_status   = str(snapshot.get("pm2_status", "")).lower()
    logs_lower   = logs.lower()

    # ── 1. Unresponsive system — can't even collect proper data ───────────────
    if not logs.strip() and not pm2_status.strip():
        print(f"  ⚡ [triage] ESCALATE — no logs and no PM2 status. System unreachable?")
        return {**state, "triage_result": "escalate", "triage_reason": "Empty logs and empty PM2 status — system may be unresponsive"}

    # ── 2. No PM2 process at all → BOOT_FAILURE (most common case) ───────────
    no_process = (
        "no process found" in pm2_status
        or ("online" not in pm2_status and "stopped" not in pm2_status and "errored" not in pm2_status)
        or not pm2_status.strip()
    )
    if no_process:
        diagnosis = _make_boot_failure_diagnosis(project_root, app_name)
        print(f"  ⚡ [triage] TRIVIAL — BOOT_FAILURE detected heuristically (no PM2 process). Skipping Gemini.")
        return {**state, "triage_result": "trivial", "triage_reason": "No PM2 process detected", "diagnosis": diagnosis}

    # ── 3. PM2 process errored + pattern match in logs ────────────────────────
    has_error_process = "errored" in pm2_status or "stopped" in pm2_status

    if has_error_process:
        for pattern, error_type, severity in _PATTERN_MAP:
            m = pattern.search(logs)
            if m:
                missing = m.group(1) if error_type == "MODULE_NOT_FOUND" and m.lastindex else ""
                diagnosis = _make_pattern_diagnosis(
                    error_type=error_type,
                    severity=severity,
                    match_text=m.group(0),
                    missing=missing,
                    project_root=project_root,
                    app_name=app_name,
                )
                print(f"  ⚡ [triage] TRIVIAL — {error_type} matched pattern directly. Skipping Gemini.")
                return {**state, "triage_result": "trivial", "triage_reason": f"Pattern match: {error_type}", "diagnosis": diagnosis}

    # ── 4. Everything else needs Gemini ───────────────────────────────────────
    print(f"  ⚡ [triage] COMPLEX — no trivial match. Routing to deep diagnosis.")
    return {**state, "triage_result": "complex", "triage_reason": "No heuristic match — Gemini needed"}


# ── Route function for graph ────────────────────────────────────────────────────

def route_after_triage(state: dict) -> str:
    return state.get("triage_result", "complex")


# ── Heuristic diagnosis builders ───────────────────────────────────────────────

def _make_boot_failure_diagnosis(project_root: str, app_name: str) -> dict:
    return {
        "error_type":       "BOOT_FAILURE",
        "root_cause":       "Application is not running in PM2 — no active process found.",
        "severity":         "critical",
        "confidence":       0.90,
        "affected_service": app_name,
        "missing_path":     None,
        "resolved_absolute": None,
        "actions": [
            {"action": "list_directory", "target": project_root,
             "reason": "Verify project files and package.json exist",
             "risk_level": "low", "reversible": True, "params": {}},
            {"action": "read_file", "target": f"{project_root}/package.json",
             "reason": "Read start script to confirm correct pm2 command",
             "risk_level": "low", "reversible": True, "params": {}},
            {"action": "pm2_start", "target": "npm",
             "params": {"name": app_name, "args": "-- start"},
             "reason": "Start app via PM2 using npm start",
             "risk_level": "low", "reversible": True},
        ],
        "reasoning": "Triage heuristic: PM2 has no registered process. Standard boot-failure recovery.",
        "_source": "triage_heuristic",
    }


def _make_pattern_diagnosis(error_type: str, severity: str, match_text: str,
                             missing: str, project_root: str, app_name: str) -> dict:
    if error_type == "MODULE_NOT_FOUND":
        actions = [
            {"action": "install_modules", "target": project_root,
             "reason": f"Install missing module: {missing}",
             "risk_level": "low", "reversible": True, "params": {}},
            {"action": "restart_service", "target": app_name,
             "reason": "Restart after npm install",
             "risk_level": "low", "reversible": True, "params": {}},
        ]
        root_cause = f"Missing npm module: {missing or 'see logs'}"
    elif error_type == "PORT_IN_USE":
        actions = [
            {"action": "kill_process", "target": "3000",
             "reason": "Free the port blocked by a stale process",
             "risk_level": "medium", "reversible": False, "params": {}},
            {"action": "restart_service", "target": app_name,
             "reason": "Restart after port freed",
             "risk_level": "low", "reversible": True, "params": {}},
        ]
        root_cause = "Port already in use — stale process blocking startup"
    else:
        actions = [
            {"action": "read_logs", "target": app_name,
             "reason": "Gather full error context",
             "risk_level": "low", "reversible": True, "params": {}},
        ]
        root_cause = f"{error_type}: {match_text[:120]}"

    return {
        "error_type":        error_type,
        "root_cause":        root_cause,
        "severity":          severity,
        "confidence":        0.80,
        "affected_service":  app_name,
        "missing_path":      missing or None,
        "resolved_absolute": None,
        "actions":           actions,
        "reasoning":         f"Triage heuristic: pattern matched '{match_text[:80]}'",
        "_source":           "triage_heuristic",
    }
