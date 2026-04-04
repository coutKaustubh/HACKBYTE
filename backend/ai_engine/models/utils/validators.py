"""
models/utils/validators.py — Shared utility functions for data models.

Keeps model files (intent.py, events.py, etc.) focused purely on schema;
common logic like timestamp injection, truncation, and serialization
lives here and is tested independently.
"""

import json
from datetime import datetime, timezone
from typing import Any


# ── Timestamp ─────────────────────────────────────────────────────────────────

def auto_timestamp() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ── String helpers ────────────────────────────────────────────────────────────

def truncate_str(value: str, max_chars: int = 300, suffix: str = "…") -> str:
    """Truncate a string to `max_chars`, appending `suffix` if clipped."""
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + suffix


# ── Serialization ─────────────────────────────────────────────────────────────

def safe_serialize(obj: Any, indent: int = 2) -> str:
    """
    JSON-serialize any object, converting non-serializable types to strings.
    Useful for embedding model instances in log payloads or prompts.
    """
    return json.dumps(obj, indent=indent, default=str)


# ── Dict helpers ──────────────────────────────────────────────────────────────

def compact_dict(d: dict, max_str: int = 300, max_list: int = 5) -> dict:
    """
    Return a copy of `d` with large strings truncated and long lists clipped.
    Useful for pretty-printing state snapshots in logs.
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > max_str:
            result[k] = truncate_str(v, max_str)
        elif isinstance(v, list) and len(v) > max_list:
            result[k] = v[:max_list] + [f"… +{len(v) - max_list} more"]
        else:
            result[k] = v
    return result


# ── Intent helpers ────────────────────────────────────────────────────────────

def build_intent_id(incident_id: str, step: int, suffix: str = "") -> str:
    """Canonical intent ID generator used by plan_node."""
    base = f"int-{incident_id}-{step:03d}"
    return f"{base}-{suffix}" if suffix else base
