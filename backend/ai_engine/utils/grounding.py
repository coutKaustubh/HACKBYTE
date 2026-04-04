"""
utils/grounding.py — Extract verified facts from already-collected snapshot data.

Purpose: give Gemini concrete, real values (service names, node version, npm scripts)
so it doesn't guess. All extraction is purely from strings already in state —
NO additional SSH calls.

Ground truth we inject:
  - Real PM2 process names + their status (online / errored / stopped)
  - Actual Node.js version from snapshot
  - npm start script from package.json text (if already read)
  - Failed systemd services

Design principle: soft grounding — we tell Gemini "here are the real values",
but we don't restrict it so hard it can't handle edge cases.
"""

import re
from typing import Optional


# ── PM2 service extraction ─────────────────────────────────────────────────────

# Matches a row in `pm2 status --no-color` table
# Example:  │ 0  │ sharad_vyas_portfolio │ default │ ... │ online │
_PM2_ROW_RE = re.compile(
    r"[│|]\s*(\d+)\s*[│|]\s*([\w._-]+)\s*[│|].*?[│|]\s*(online|stopped|errored|launching|one_launch_status)\s*[│|]",
    re.IGNORECASE,
)


def extract_pm2_services(pm2_status: str) -> list[dict]:
    """
    Parse `pm2 status --no-color` output and return a list of:
      {"id": "0", "name": "sharad_vyas_portfolio", "status": "online"}
    """
    services = []
    for m in _PM2_ROW_RE.finditer(pm2_status):
        services.append({
            "id":     m.group(1).strip(),
            "name":   m.group(2).strip(),
            "status": m.group(3).strip().lower(),
        })
    return services


def fmt_pm2_services(services: list[dict]) -> str:
    """Format PM2 service list as a compact grounding string for prompts."""
    if not services:
        return "(no processes registered in PM2)"
    lines = [f"  - name='{s['name']}' id={s['id']} status={s['status']}" for s in services]
    return "\n".join(lines)


# ── Node.js version extraction ─────────────────────────────────────────────────

def extract_node_version(snapshot: dict) -> str:
    """Try to find Node version from uptime or process output in snapshot."""
    # Sometimes in top_processes or recent_errors
    for key in ("top_processes", "recent_errors", "pm2_status"):
        val = snapshot.get(key, "")
        m = re.search(r"node[/\s]+v?([\d.]+)", val, re.IGNORECASE)
        if m:
            return f"v{m.group(1)}"
    return "unknown"


# ── npm start script extraction ────────────────────────────────────────────────

def extract_start_script(package_json_text: str) -> Optional[str]:
    """Extract the 'start' script from package.json text (already fetched)."""
    m = re.search(r'"start"\s*:\s*"([^"]+)"', package_json_text)
    return m.group(1) if m else None


def extract_build_script(package_json_text: str) -> Optional[str]:
    m = re.search(r'"build"\s*:\s*"([^"]+)"', package_json_text)
    return m.group(1) if m else None


# ── Master grounding context builder ──────────────────────────────────────────

def build_grounded_context(snapshot: dict, config_files: dict = None) -> dict:
    """
    Build a grounded context dict from snapshot + config files.
    Used by prompts.py to inject real values into Gemini prompts.

    Args:
        snapshot:     state['system_snapshot'] from collect_node
        config_files: state['config_files'] — may contain package_json text
    """
    config_files = config_files or {}
    pm2_status   = snapshot.get("pm2_status", "")
    services     = extract_pm2_services(pm2_status)

    pkg_json     = config_files.get("package_json", "")
    start_script = extract_start_script(pkg_json)
    build_script = extract_build_script(pkg_json)

    failed_raw   = snapshot.get("failed_services", "")
    # Extract just service names from systemd --failed output
    failed_names = re.findall(r"([\w@.-]+\.service)", failed_raw)

    return {
        "pm2_services":      services,
        "pm2_services_fmt":  fmt_pm2_services(services),
        "node_version":      extract_node_version(snapshot),
        "start_script":      start_script or "npm start",
        "build_script":      build_script or "npm run build",
        "failed_services":   failed_names,
        "failed_services_fmt": ", ".join(failed_names) if failed_names else "none",
    }


def grounded_context_str(ctx: dict) -> str:
    """Format grounded context as a prompt section string."""
    svc_section = (
        f"  PM2 processes:\n{ctx['pm2_services_fmt']}\n"
        f"  node version   : {ctx['node_version']}\n"
        f"  npm start cmd  : {ctx['start_script']}\n"
        f"  npm build cmd  : {ctx['build_script']}\n"
        f"  systemd failed : {ctx['failed_services_fmt']}"
    )
    return svc_section
