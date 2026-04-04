"""
nodes/utils/routing.py — Graph routing logic and loop-control helpers.

Keeps graph.py focused on wiring and execute.py on execution by isolating
the 'should we continue?' decision into testable pure functions.
"""

from __future__ import annotations


# ── Loop control ──────────────────────────────────────────────────────────────

def has_same_actions_been_tried(state: dict, current_results: list[dict]) -> bool:
    """
    Return True if the same set of (non-skipped) actions was already executed
    in a previous retry and still failed.

    This prevents pointless retry loops where the agent would keep re-running
    identical actions that have no chance of producing a different outcome.
    """
    current_actions = tuple(sorted(
        r.get("action", "")
        for r in current_results
        if r.get("status") != "SKIPPED"
    ))
    if not current_actions:
        return False
    prev_attempts = state.get("_prev_action_sets", [])
    return current_actions in prev_attempts


def should_terminate_loop(state: dict) -> bool:
    """
    Return True if the retry loop should be stopped.

    Criteria (any one is sufficient):
      1. incident is resolved  (all actions succeeded)
      2. max retries (3) reached
      3. same action set already tried and failed  (dedup guard)
    """
    if state.get("incident_resolved", False):
        return True
    if state.get("retries", 0) >= 3:
        return True
    exec_results = state.get("execution_results", [])
    if has_same_actions_been_tried(state, exec_results):
        return True
    return False


# ── Graph edge function ────────────────────────────────────────────────────────

def continue_or_end(state: dict) -> str:
    """
    LangGraph conditional-edge function called after execute_node.
    Returns 'end' or 'continue' (→ collect for a fresh retry).

    Usage in graph.py:
        graph.add_conditional_edges("execute", continue_or_end, {"continue": "collect", "end": END})
    """
    if should_terminate_loop(state):
        return "end"
    return "continue"
