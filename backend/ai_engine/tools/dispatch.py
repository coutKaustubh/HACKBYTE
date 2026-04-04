"""
tools/dispatch.py — Action dispatch table for the execute node.

Separating the dispatch map from VMTools means:
  - Adding new actions = editing ONE file (not hunting through vm_tools.py)
  - Execute node imports dispatch, not VMTools directly
  - Each action handler is a named lambda that's easy to trace
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.vm_tools import VMTools


def build_dispatch_map(vm: "VMTools") -> dict:
    """
    Return a mapping of action_name → callable(target, params) → dict.

    All callables return a result dict with at minimum:
      { "action": str, "target": str, "status": str, "output": str }
    """
    return {
        # ── Process management ───────────────────────────────────────
        "restart_service":    lambda t, p: vm.restart_service(t),
        "pm2_start":          lambda t, p: vm.pm2_start(t, p),
        "kill_process":       lambda t, p: vm.kill_process(t),

        # ── Config / deploy ──────────────────────────────────────────
        "edit_config":        lambda t, p: vm.edit_config(t, p),
        "fix_import_path":    lambda t, p: vm.edit_config(t, p),   # alias
        "rollback_deploy":    lambda t, p: vm.rollback_deploy(t),
        "redeploy_app":       lambda t, p: vm.redeploy_app(p.get("message", "AI Patch")),

        # ── Observation ──────────────────────────────────────────────
        "read_logs":          lambda t, p: {"action": "read_logs",   "target": t, "status": "SUCCESS", "output": vm.read_service_logs(t)},
        "read_file":          lambda t, p: {"action": "read_file",   "target": t, "status": "SUCCESS", "output": vm.read_file(t)},
        "list_directory":     lambda t, p: vm.list_directory(t),

        # ── File operations ──────────────────────────────────────────
        "write_file":         lambda t, p: vm.write_file(t, p.get("content", "")),
        "create_model_file":  lambda t, p: vm.write_file(t, p.get("content", "")),
        "rename_file":        lambda t, p: vm.rename_file(t, p),

        # ── Dependency / build ───────────────────────────────────────
        "fix_missing_module":  lambda t, p: vm.install_dependency(t),
        "install_dependency":  lambda t, p: vm.install_dependency(t),
        "install_modules":     lambda t, p: vm.install_modules(t),
        "build_app":           lambda t, p: vm.build_app(t),
    }


def dispatch_action(vm: "VMTools", action: str, target: str, params: dict) -> dict:
    """
    Look up and execute an action from the dispatch map.
    Returns a FAILED result dict for unknown actions.
    """
    dispatch_map = build_dispatch_map(vm)
    fn = dispatch_map.get(action)
    if not fn:
        return {
            "action": action,
            "target": target,
            "status": "FAILED",
            "output": f"Unknown action: '{action}'. Not in approved dispatch map.",
        }
    return fn(target, params)
