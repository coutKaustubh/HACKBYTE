"""
nodes/utils/state_helpers.py — Pure functions for reading and mutating pipeline state.

All node files receive and return a plain `dict` — these helpers centralise the
repeated pattern of extracting intents, filtering results, and building summaries
so nodes stay thin and readable.
"""

from __future__ import annotations


# ── Intent filtering ──────────────────────────────────────────────────────────

def get_allowed_intents(state: dict) -> list[dict]:
    """
    Return only the intents whose enforcement result was ALLOWED.
    Preserves original order.
    """
    allowed_ids = {
        r["intent_id"]
        for r in state.get("enforcement_results", [])
        if r["decision"] == "ALLOWED"
    }
    return [
        intent
        for intent in state.get("intent_plan", [])
        if intent["intent_id"] in allowed_ids
    ]


# ── Execution result helpers ──────────────────────────────────────────────────

def get_exec_results_by_status(results: list[dict], status: str) -> list[dict]:
    """Filter execution results list by a given status string."""
    return [r for r in results if r.get("status") == status]


def all_succeeded(results: list[dict]) -> bool:
    """Return True only if every result has status SUCCESS (empty list → True)."""
    return all(r.get("status") == "SUCCESS" for r in results)


# ── Summary builder ───────────────────────────────────────────────────────────

def build_execution_summary(state: dict, execution_results: list[dict]) -> dict:
    """
    Produce the canonical summary dict that is stored in state['summary_data']
    and emitted to the logger.
    """
    enforcement = state.get("enforcement_results", [])
    blocked      = [r for r in enforcement if r["decision"] == "BLOCKED"]
    allowed      = [r for r in enforcement if r["decision"] == "ALLOWED"]
    succeeded    = get_exec_results_by_status(execution_results, "SUCCESS")
    skipped      = get_exec_results_by_status(execution_results, "SKIPPED")

    service = (state.get("diagnosis") or {}).get("affected_service") or "System"

    return {
        "incident_id":       state.get("incident_id", "unknown"),
        "root_cause":        (state.get("diagnosis") or {}).get("root_cause", ""),
        "severity":          (state.get("diagnosis") or {}).get("severity", ""),
        "actions_allowed":   len(allowed),
        "actions_blocked":   len(blocked),
        "actions_succeeded": len(succeeded),
        "actions_skipped":   len(skipped),
        "blocked_details":   blocked,
        "code_patch":        state.get("code_patch_applied"),
        "summary": (
            f"{service} incident resolved. "
            f"{len(succeeded)} fix(es) applied, "
            f"{len(skipped)} skipped (reactive), "
            f"{len(blocked)} dangerous action(s) blocked by policy."
        ),
    }


# ── Retry dedup tracking ──────────────────────────────────────────────────────

def track_action_set(state: dict, execution_results: list[dict]) -> list[tuple]:
    """
    Accumulate the frozenset of actions executed this retry into
    state['_prev_action_sets'] so the routing layer can detect repeated failures.

    Returns the updated _prev_action_sets list.
    """
    current = tuple(sorted(
        r.get("action", "")
        for r in execution_results
        if r.get("status") != "SKIPPED"
    ))
    prev = list(state.get("_prev_action_sets", []))
    if current:
        prev.append(current)
    return prev
