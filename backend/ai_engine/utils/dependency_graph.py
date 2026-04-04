"""
utils/dependency_graph.py — Service dependency awareness.

Loads policies/service_dependencies.json and answers:
  "Given that service X has a problem, are any of its upstream dependencies
   also down? If yes, suppress auto-fix on X — fix the dependency first."

This prevents 5 agents all trying to fix nginx/backend when the real issue
is postgres being down.
"""

import json
import os
from typing import Optional


_DEP_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "policies", "service_dependencies.json")
)


class DependencyGraph:
    def __init__(self):
        self._graph: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(_DEP_JSON, encoding="utf-8") as f:
                data = json.load(f)
            self._graph = data.get("dependencies", {})
        except FileNotFoundError:
            print(f"[DependencyGraph] {_DEP_JSON} not found — dependency checks disabled.")
        except Exception as e:
            print(f"[DependencyGraph] Failed to load: {e}")

    def dependencies_of(self, service: str) -> list[str]:
        """Return list of services that `service` depends on."""
        return self._graph.get(service, [])

    def should_suppress(self, service: str, snapshot: dict) -> Optional[dict]:
        """
        Return a suppression dict if any dependency of `service` appears to be
        down (based on PM2 status or failed_services in snapshot).
        Returns None if no suppression needed.
        """
        if not service or service in ("auto-detected", "build", "unknown"):
            return None

        deps = self.dependencies_of(service)
        if not deps:
            return None

        pm2_status       = str(snapshot.get("pm2_status", "")).lower()
        failed_services  = str(snapshot.get("failed_services", "")).lower()

        down_deps = []
        for dep in deps:
            dep_lower = dep.lower()
            # Check if dep appears in PM2 as errored/stopped, or in systemd failed list
            if (
                (dep_lower in pm2_status and "online" not in _extract_status_for(dep_lower, pm2_status))
                or dep_lower in failed_services
            ):
                down_deps.append(dep)

        if not down_deps:
            return None

        return {
            "error_type":       "DEPENDENCY_DOWN",
            "suppressed":       True,
            "affected_service": service,
            "down_dependencies": down_deps,
            "root_cause": (
                f"Service '{service}' depends on {down_deps} which appear to be down. "
                f"Fix {down_deps} first — auto-fix of '{service}' is suppressed."
            ),
            "severity":   "high",
            "confidence": 1.0,
            "actions":    [],
            "message": (
                f"🕸️  Dependency suppression: '{service}' requires {down_deps}. "
                f"Skipping auto-fix to avoid redundant attempts."
            ),
        }

    def is_root_service(self, service: str) -> bool:
        """True if service has no dependencies (it IS the root)."""
        return len(self.dependencies_of(service)) == 0


def _extract_status_for(dep: str, pm2_block: str) -> str:
    """Try to find the status word near the dependency name in PM2 output."""
    idx = pm2_block.find(dep)
    if idx == -1:
        return ""
    return pm2_block[idx: idx + 80]
