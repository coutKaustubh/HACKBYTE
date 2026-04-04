"""
utils/formatters.py — Pure string formatting utilities for the logger.

These have no side-effects (no print calls) and can be imported and tested
independently of the rest of the logger.
"""

import json
from datetime import datetime
from utils.colors import DIM, RESET


def ts() -> str:
    """Current local time as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def divider(char: str = "─", width: int = 64) -> str:
    """Return a full-width terminal divider line."""
    return DIM + char * width + RESET


def fmt_dict(d: dict, indent: int = 4) -> str:
    """
    Pretty-print a dict, truncating large strings and long lists so they
    don't flood the terminal.
    """
    small = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > 300:
            small[k] = v[:300] + "…"
        elif isinstance(v, list) and len(v) > 5:
            small[k] = v[:5] + [f"… +{len(v)-5} more"]
        else:
            small[k] = v
    return json.dumps(small, indent=indent, default=str)


def risk_color(risk: str, colors) -> str:
    """Map a risk_level string to an ANSI color code."""
    risk = risk.upper()
    if risk == "CRITICAL":
        return colors.RED
    if risk in ("HIGH", "MEDIUM"):
        return colors.YELLOW
    return colors.GREEN
