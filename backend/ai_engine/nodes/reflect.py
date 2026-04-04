"""
nodes/reflect.py — Chain-of-Thought self-critique node.

Sits between diagnose and plan. Acts as a "skeptical peer reviewer":
  - APPROVE  → diagnosis is sound, pass through unchanged
  - MODIFY   → adjust actions (remove redundant/wrong ones, add missing ones)
  - ESCALATE → too uncertain or risky, defer to human

This node prevents the classic LLM failure mode of "confident but wrong" —
Gemini critiques its OWN diagnosis before any action is executed.

When is reflect SKIPPED (fast-path)?
  - Triage-sourced diagnosis (already high-confidence heuristic) → skip
  - Single action plan (nothing complex to review)
  - Error type is BOOT_FAILURE with confidence > 0.85 (trivial, safe)
  - Human escalation already set (no point reviewing what won't execute)

Cost: 1 Gemini call, but ~3x shorter prompt than diagnose.
      Cached by SHA-256(diagnosis_hash + tree_hash) → TTL 10 min.
"""

import json
import re
from tools.gemini_tools import GeminiTools
from tools.prompts      import build_reflect_prompt
from utils.cache        import TTLCache
from utils.grounding    import build_grounded_context, grounded_context_str
from utils.response_validator import ALLOWED_ACTIONS

gemini = GeminiTools()

# Separate cache for reflect results
_reflect_cache = TTLCache(ttl=600, max_size=64)

# Error types so trivial we don't bother reflecting
_SKIP_REFLECT_TYPES = {"BOOT_FAILURE"}


def reflect_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    diagnosis   = state.get("diagnosis", {})
    actions     = diagnosis.get("actions", [])
    error_type  = diagnosis.get("error_type", "UNKNOWN")
    confidence  = float(diagnosis.get("confidence", 0.5))

    # ── Fast-path skips ────────────────────────────────────────────────────────
    skip_reason = _should_skip(state, error_type, confidence, actions)
    if skip_reason:
        print(f"  🪞 [reflect] SKIPPED — {skip_reason}")
        return {**state, "reflect_verdict": "APPROVE", "reflect_reasoning": skip_reason}

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = TTLCache.make_key(
        json.dumps(diagnosis, default=str),
        state.get("project_tree", "")[:1000],
    )
    cached = _reflect_cache.get(cache_key)
    if cached:
        print(f"  🪞 [reflect] Cache HIT — reusing critique.")
        return _apply_reflect(state, cached, incident_id)

    # ── Gemini self-critique ───────────────────────────────────────────────────
    grounded = build_grounded_context(
        snapshot=state.get("system_snapshot", {}),
        config_files=state.get("config_files", {}),
    )
    gemini.incident_id = incident_id

    prompt = build_reflect_prompt(
        diagnosis=diagnosis,
        project_tree=state.get("project_tree", ""),
        grounded_context=grounded_context_str(grounded),
    )

    raw = gemini._call(prompt, call_type="reflect")
    try:
        critique = json.loads(raw)
    except Exception:
        # Can't parse → safe default: APPROVE and move on
        print(f"  🪞 [reflect] Could not parse critique — defaulting to APPROVE")
        critique = {"verdict": "APPROVE", "reasoning": "Parse failed — defaulted to approve", "confidence_adjustment": 0.0}

    _reflect_cache.set(cache_key, critique)
    return _apply_reflect(state, critique, incident_id)


# ── Route function for graph ────────────────────────────────────────────────────

def route_after_reflect(state: dict) -> str:
    """
    LangGraph conditional edge after reflect_node.
    Returns: "plan" | "code_fix" | "escalate"
    """
    verdict = state.get("reflect_verdict", "APPROVE")

    if verdict == "ESCALATE" or state.get("human_escalation"):
        return "escalate"

    diagnosis  = state.get("diagnosis", {})
    error_type = diagnosis.get("error_type", "UNKNOWN")

    from nodes.code_fix import CODE_ERROR_TYPES
    if error_type in CODE_ERROR_TYPES and not state.get("dependency_suppressed"):
        return "code_fix"

    return "plan"


# ── Apply critique to state ────────────────────────────────────────────────────

def _apply_reflect(state: dict, critique: dict, incident_id: str) -> dict:
    verdict    = critique.get("verdict", "APPROVE")
    reasoning  = critique.get("reasoning", "")
    adj        = float(critique.get("confidence_adjustment", 0.0))
    threshold  = float(__import__("os").getenv("CONFIDENCE_THRESHOLD", "0.55"))

    print(f"  🪞 [reflect] Verdict: {verdict}  |  {reasoning[:120]}")

    diagnosis = dict(state.get("diagnosis", {}))

    # ── Confidence adjustment ─────────────────────────────────────────────────
    if adj != 0.0:
        old_conf          = float(diagnosis.get("confidence", 0.5))
        diagnosis["confidence"] = round(max(0.05, min(1.0, old_conf + adj)), 2)
        print(f"  🪞 [reflect] Confidence adjusted {old_conf:.2f} → {diagnosis['confidence']:.2f}")

    # ── MODIFY: apply action changes ──────────────────────────────────────────
    if verdict == "MODIFY":
        actions = list(diagnosis.get("actions", []))

        # Remove flagged indices (reverse sort to avoid index shifting)
        remove_indices = sorted(set(critique.get("remove_action_indices", [])), reverse=True)
        for idx in remove_indices:
            if 0 <= idx < len(actions):
                removed = actions.pop(idx)
                print(f"  🪞 [reflect] Removed action[{idx}]: {removed.get('action')} → {removed.get('target')}")

        # Apply modifications to existing actions
        for mod in critique.get("modified_actions", []):
            idx = mod.get("index")
            if idx is not None and 0 <= idx < len(actions):
                for k, v in mod.items():
                    if k != "index":
                        actions[idx][k] = v
                print(f"  🪞 [reflect] Modified action[{idx}]")

        # Add new actions (validate action names first)
        for new_action in critique.get("add_actions", []):
            name = new_action.get("action", "")
            if name in ALLOWED_ACTIONS:
                actions.append(new_action)
                print(f"  🪞 [reflect] Added action: {name} → {new_action.get('target')}")
            else:
                print(f"  🪞 [reflect] Rejected add_action '{name}' — not in allowed list")

        diagnosis["actions"] = actions

    # ── ESCALATE: trigger human handoff ───────────────────────────────────────
    human_escalation = (verdict == "ESCALATE") or (diagnosis.get("confidence", 1.0) < threshold)

    return {
        **state,
        "diagnosis":        diagnosis,
        "reflect_verdict":  verdict,
        "reflect_reasoning": reasoning,
        "human_escalation": human_escalation,
    }


# ── Skip conditions ────────────────────────────────────────────────────────────

def _should_skip(state: dict, error_type: str, confidence: float, actions: list) -> str:
    if state.get("human_escalation"):
        return "human escalation already active"
    if state.get("dependency_suppressed"):
        return "dependency suppressed — nothing to reflect on"
    if diagnosis := state.get("diagnosis", {}):
        if diagnosis.get("_source") == "triage_heuristic" and confidence >= 0.80:
            return f"triage heuristic result (confidence={confidence:.0%}) — trusted, no critique needed"
    if error_type in _SKIP_REFLECT_TYPES and confidence >= 0.85:
        return f"trivial {error_type} with high confidence — skipping critique"
    if len(actions) <= 1:
        return "single action plan — no complexity to review"
    return ""   # don't skip — run reflect
