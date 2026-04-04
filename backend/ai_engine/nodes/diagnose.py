"""
nodes/diagnose.py — Diagnosis node.

New capabilities:
  - Gemini confidence scoring: if confidence < CONFIDENCE_THRESHOLD, human escalation instead of auto-fix
  - Telemetry recording: every incident logged for trend analysis
  - Recurring detection: flag if same error on same service keeps coming back
  - Dependency graph: suppress fix if a root dependency is already being handled
  - Cost tracking: gemini.incident_id set here so all downstream calls are attributed
  - Diagnosis cache: SHA-256(logs + snapshot) → skip Gemini on identical log sets
"""

import os
import json
from dotenv import load_dotenv
from tools.gemini_tools import GeminiTools
from utils.logger        import log_diagnosis_ready, log_human_escalation, log_recurring_alert
from utils.cache         import diagnosis_cache, TTLCache
from utils.telemetry     import telemetry
from utils.dependency_graph    import DependencyGraph
from utils.grounding           import build_grounded_context, grounded_context_str
from utils.response_validator  import validate_diagnosis, adjust_confidence_for_log_quality

load_dotenv()

gemini     = GeminiTools()
dep_graph  = DependencyGraph()

_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))


def diagnose_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    service     = state.get("service_hint", "unknown")

    logs     = state.get("raw_logs", "")
    snapshot = state.get("system_snapshot", {})

    # ── Wire incident_id into gemini so all calls are cost-attributed ──────────
    gemini.incident_id = incident_id

    # ── Fast-path heuristic (no Gemini needed) ─────────────────────────────────
    pm2_logs_empty     = len(logs.strip()) < 150 or "No process found" in logs
    pm2_status         = str(snapshot.get("pm2_status", ""))
    no_process_running = "online" not in pm2_status.lower()

    if pm2_logs_empty and no_process_running:
        project_root = os.getenv("PROJECT_ROOT", "/root/app")
        app_name     = os.path.basename(project_root.rstrip("/")) or "app"

        diagnosis = {
            "error_type": "BOOT_FAILURE",
            "root_cause": "The application is not running. Process missing and no logs found.",
            "confidence": 0.95,   # heuristic is high-confidence
            "affected_service": app_name,
            "severity": "critical",
            "actions": [
                {"action": "list_directory", "target": project_root,
                 "reason": "Check if package.json and run scripts exist",
                 "risk_level": "low", "reversible": True},
                {"action": "read_file", "target": project_root + "/package.json",
                 "reason": "Verify entry point and start script",
                 "risk_level": "low", "reversible": True},
                {"action": "pm2_start", "target": "npm",
                 "params": {"name": app_name, "args": "-- start"},
                 "reason": "Start the application via pm2 using npm start script",
                 "risk_level": "low", "reversible": True},
            ],
        }
        return _finish(state, incident_id, service, diagnosis, from_cache=False)

    # ── Dependency graph check ─────────────────────────────────────────────────
    dep_block = dep_graph.should_suppress(service, snapshot)
    if dep_block:
        print(f"  🕸️  [diagnose] Dependency suppression: {dep_block['message']}")
        return {
            **state,
            "diagnosis":        dep_block,
            "human_escalation": False,
            "dependency_suppressed": True,
        }

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = TTLCache.make_key(logs, json.dumps(snapshot, default=str))
    cached    = diagnosis_cache.get(cache_key)

    if cached is not None:
        print(f"  💾 [diagnose] Cache HIT — reusing diagnosis. (stats: {diagnosis_cache.stats()})")
        return _finish(state, incident_id, service, cached, from_cache=True)

    # ── Build grounded context (no SSH — from snapshot already in state) ─────
    grounded = build_grounded_context(
        snapshot=snapshot,
        config_files=state.get("config_files", {}),
    )
    grounded_str = grounded_context_str(grounded)

    # ── Full Gemini diagnosis ──────────────────────────────────────────────────
    print(f"  🤖 [diagnose] Cache MISS — calling Gemini. (stats: {diagnosis_cache.stats()})")

    diagnosis = gemini.diagnose(
        logs=logs,
        snapshot=snapshot,
        configs=state.get("config_files", {}),
        project_tree=state.get("project_tree", ""),
        grounded_context=grounded_str,
    )
    diagnosis_cache.set(cache_key, diagnosis)

    return _finish(state, incident_id, service, diagnosis, from_cache=False)


# ── Shared finish logic ────────────────────────────────────────────────────────

def _finish(state: dict, incident_id: str, service: str, diagnosis: dict, from_cache: bool) -> dict:
    # ── Post-processing: validate + ground-truth check ────────────────────────
    # Run on every diagnosis (cached or fresh) so stale aliases get fixed too
    diagnosis = validate_diagnosis(diagnosis, project_tree=state.get("project_tree", ""))
    diagnosis = adjust_confidence_for_log_quality(diagnosis, state.get("raw_logs", ""))

    error_type = diagnosis.get("error_type", "UNKNOWN")
    confidence = float(diagnosis.get("confidence", 1.0))
    affected   = diagnosis.get("affected_service") or service or "unknown"

    # Record in telemetry
    telemetry.record_incident(incident_id, error_type, affected, confidence)

    # Check for recurring incident
    recurring = telemetry.check_recurring(affected, error_type)
    if recurring:
        log_recurring_alert(incident_id, recurring)

    log_diagnosis_ready(incident_id, diagnosis)

    # ── Confidence gate ────────────────────────────────────────────────────────
    human_escalation = confidence < _CONFIDENCE_THRESHOLD
    if human_escalation:
        log_human_escalation(incident_id, confidence, _CONFIDENCE_THRESHOLD, diagnosis)

    return {
        **state,
        "diagnosis":          diagnosis,
        "human_escalation":   human_escalation,
        "recurring_alert":    recurring,
        "diagnosis_from_cache": from_cache,
    }
