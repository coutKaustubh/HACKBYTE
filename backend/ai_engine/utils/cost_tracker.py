"""
utils/cost_tracker.py — Per-incident Gemini API token usage & cost estimation.

Gemini 2.5 Flash pricing (as of April 2026):
  Input  tokens: $0.075 per 1M tokens
  Output tokens: $0.30  per 1M tokens

Token estimation: uses response.usage_metadata when available from the SDK,
falls back to character-count heuristic (1 token ≈ 4 chars).
"""

import time
from collections import defaultdict


# ── Pricing (USD per 1M tokens) ───────────────────────────────────────────────
_INPUT_COST_PER_M  = 0.075
_OUTPUT_COST_PER_M = 0.30

# ── Chars-per-token fallback ratio ────────────────────────────────────────────
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Rough token count when SDK usage_metadata is unavailable."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _usd(input_tokens: int, output_tokens: int) -> float:
    cost = (
        (input_tokens  / 1_000_000) * _INPUT_COST_PER_M
        + (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    )
    return round(cost, 6)


class IncidentCost:
    """Accumulates token usage across all Gemini calls in one incident."""

    def __init__(self, incident_id: str):
        self.incident_id    = incident_id
        self.calls:  list[dict] = []
        self.started_at     = time.time()

    def record(
        self,
        call_type:     str,   # "diagnose" | "code_patch" | "reactive"
        input_tokens:  int,
        output_tokens: int,
    ) -> None:
        cost = _usd(input_tokens, output_tokens)
        self.calls.append({
            "call_type":     call_type,
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "cost_usd":      cost,
        })

    def total(self) -> dict:
        t_in  = sum(c["input_tokens"]  for c in self.calls)
        t_out = sum(c["output_tokens"] for c in self.calls)
        return {
            "incident_id":        self.incident_id,
            "gemini_calls":       len(self.calls),
            "total_input_tokens": t_in,
            "total_output_tokens":t_out,
            "estimated_cost_usd": _usd(t_in, t_out),
            "duration_secs":      round(time.time() - self.started_at, 1),
            "call_breakdown":     self.calls,
        }


class CostTracker:
    """
    Global cost tracker — one IncidentCost per incident_id.

    Usage (from GeminiTools._call_tracked):
        cost_tracker.record("inc-abc123", "diagnose", in_tok=500, out_tok=200)

    Read:
        cost_tracker.incident_cost("inc-abc123")  → total dict
        cost_tracker.all_costs()                   → list of all totals
        cost_tracker.lifetime_total()              → aggregate USD
    """

    def __init__(self):
        self._incidents: dict[str, IncidentCost] = {}
        self._lifetime_usd = 0.0

    def record(
        self,
        incident_id:   str,
        call_type:     str,
        input_tokens:  int,
        output_tokens: int,
    ) -> None:
        if incident_id not in self._incidents:
            self._incidents[incident_id] = IncidentCost(incident_id)
        ic = self._incidents[incident_id]
        ic.record(call_type, input_tokens, output_tokens)
        self._lifetime_usd += _usd(input_tokens, output_tokens)
        self._lifetime_usd  = round(self._lifetime_usd, 6)

    def incident_cost(self, incident_id: str) -> dict:
        ic = self._incidents.get(incident_id)
        return ic.total() if ic else {"incident_id": incident_id, "gemini_calls": 0}

    def all_costs(self, limit: int = 50) -> list[dict]:
        return [ic.total() for ic in list(self._incidents.values())[-limit:]]

    def lifetime_total(self) -> dict:
        total_in  = sum(c["input_tokens"]  for ic in self._incidents.values() for c in ic.calls)
        total_out = sum(c["output_tokens"] for ic in self._incidents.values() for c in ic.calls)
        return {
            "incidents_tracked":   len(self._incidents),
            "total_gemini_calls":  sum(len(ic.calls) for ic in self._incidents.values()),
            "total_input_tokens":  total_in,
            "total_output_tokens": total_out,
            "lifetime_cost_usd":   self._lifetime_usd,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────
cost_tracker = CostTracker()
