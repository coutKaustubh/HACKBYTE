"""
utils/telemetry.py — Anomaly trend detection & recurring incident tracking.

Tracks:
  - How often each error_type has occurred (frequency map)
  - Whether a "fixed" incident re-occurs (recurring detection)
  - Per-service incident history (time-series of error events)

All data is in-memory (process lifetime). For persistence across restarts,
extend to write to a JSON file or append to a DB.
"""

import time
from collections import defaultdict, deque
from typing import Optional


# ── Config ─────────────────────────────────────────────────────────────────────
_RECURRENCE_WINDOW_SECS = 3600   # incident is "recurring" if it re-occurs within 1 hour
_HISTORY_MAX_PER_SERVICE = 50    # max incident records kept per service name


class IncidentRecord:
    """Single incident event stored in the telemetry log."""
    __slots__ = ("incident_id", "error_type", "service", "resolved", "timestamp", "confidence")

    def __init__(
        self,
        incident_id: str,
        error_type:  str,
        service:     str,
        confidence:  float,
    ):
        self.incident_id = incident_id
        self.error_type  = error_type
        self.service     = service or "unknown"
        self.confidence  = confidence
        self.resolved    = False
        self.timestamp   = time.time()

    def mark_resolved(self):
        self.resolved = True

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "error_type":  self.error_type,
            "service":     self.service,
            "resolved":    self.resolved,
            "confidence":  self.confidence,
            "timestamp":   self.timestamp,
            "age_secs":    round(time.time() - self.timestamp),
        }


class TelemetryStore:
    """
    In-memory telemetry store.

    Usage:
        telemetry.record_incident(incident_id, "BOOT_FAILURE", "backend", 0.9)
        telemetry.mark_resolved(incident_id)
        alert = telemetry.check_recurring("backend", "BOOT_FAILURE")
    """

    def __init__(self):
        # error_type → total count
        self._error_counts: dict[str, int] = defaultdict(int)

        # service → deque of IncidentRecord (most recent first)
        self._history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=_HISTORY_MAX_PER_SERVICE)
        )

        # incident_id → IncidentRecord (for mark_resolved lookup)
        self._by_id: dict[str, IncidentRecord] = {}

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_incident(
        self,
        incident_id: str,
        error_type:  str,
        service:     str,
        confidence:  float,
    ) -> None:
        rec = IncidentRecord(incident_id, error_type, service, confidence)
        self._error_counts[error_type] += 1
        self._history[service].appendleft(rec)
        self._by_id[incident_id] = rec

    def mark_resolved(self, incident_id: str) -> None:
        rec = self._by_id.get(incident_id)
        if rec:
            rec.mark_resolved()

    # ── Recurring detection ───────────────────────────────────────────────────

    def check_recurring(self, service: str, error_type: str) -> Optional[dict]:
        """
        Return a recurring-incident alert dict if the same error_type on the
        same service has occurred more than once within _RECURRENCE_WINDOW_SECS.
        Returns None if not recurring.
        """
        now       = time.time()
        cutoff    = now - _RECURRENCE_WINDOW_SECS
        recent    = [
            r for r in self._history[service]
            if r.error_type == error_type and r.timestamp >= cutoff
        ]
        count = len(recent)
        if count < 2:
            return None

        return {
            "recurring":    True,
            "service":      service,
            "error_type":   error_type,
            "occurrences":  count,
            "window_secs":  _RECURRENCE_WINDOW_SECS,
            "message":      (
                f"⚠️  RECURRING INCIDENT: '{error_type}' on '{service}' "
                f"has occurred {count}x in the past {_RECURRENCE_WINDOW_SECS // 60} min. "
                f"Auto-fix may not be effective — consider manual investigation."
            ),
        }

    # ── Analytics ─────────────────────────────────────────────────────────────

    def error_frequency(self) -> dict:
        """Return error_type → count map, sorted by frequency (most common first)."""
        return dict(sorted(self._error_counts.items(), key=lambda x: x[1], reverse=True))

    def service_history(self, service: str, limit: int = 20) -> list[dict]:
        """Return the last `limit` incident records for a service."""
        return [r.to_dict() for r in list(self._history[service])[:limit]]

    def all_services(self) -> list[str]:
        return list(self._history.keys())

    def summary(self) -> dict:
        total      = sum(self._error_counts.values())
        resolved   = sum(1 for r in self._by_id.values() if r.resolved)
        unresolved = len(self._by_id) - resolved
        return {
            "total_incidents":    total,
            "resolved":           resolved,
            "unresolved":         unresolved,
            "error_frequency":    self.error_frequency(),
            "services_monitored": self.all_services(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────
telemetry = TelemetryStore()
