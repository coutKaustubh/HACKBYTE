from tools.vm_tools      import VMTools
from tools.spacetime_tools import SpacetimeTools
from tools.log_tools     import fetch_deploy_logs
from utils.logger        import log_incident_started, log_logs_collected
from utils.project_tree  import tree_cache

vm = VMTools()
st = SpacetimeTools()


def collect_node(state: dict) -> dict:
    incident_id  = state["incident_id"]
    service_hint = state.get("service_hint")

    log_incident_started(incident_id, state["source"])

    # System snapshot (includes pm2_status)
    snapshot = vm.get_system_snapshot()
    configs  = vm.get_config_files()

    # ── Project file tree (cached — SSH only on miss/stale) ──────────────────
    # This is injected into Gemini prompts so AI references REAL paths only.
    project_tree = tree_cache.get(vm)

    # ── Primary: PM2 logs and status ──────────────────────────────────────────
    pm2_logs        = vm._run("pm2 logs --nostream --lines 100 2>/dev/null || pm2 logs --lines 100 2>&1 | head -200")
    pm2_status_full = vm._run("pm2 status --no-color 2>/dev/null")

    logs = f"=== PM2 Status ===\n{pm2_status_full}\n\n=== PM2 App Logs (last 100 lines) ===\n{pm2_logs}"

    # ── Secondary: systemd service logs if a specific service is hinted ───────
    if service_hint and service_hint not in ("auto-detected", "build"):
        svc_logs = vm.read_service_logs(service_hint, lines=100)
        logs += f"\n\n=== {service_hint} (journalctl) ===\n{svc_logs}"

    # ── External log source (Logtail / Axiom etc.) ────────────────────────────
    external = fetch_deploy_logs()
    if external:
        logs = (
            "=== Deploy / app logs (LOG_SOURCE_URL) ===\n"
            f"{external}\n\n"
            f"{logs}"
        )

    # ── Custom logs from /run-build endpoint ──────────────────────────────────
    custom_logs = state.get("custom_logs", "")
    if custom_logs:
        logs = (
            "=== Custom Build Logs ===\n"
            f"{custom_logs}\n\n"
            f"{logs}"
        )

    log_logs_collected(
        incident_id,
        log_length=len(logs),
        pm2_snippet=pm2_status_full[:120].replace("\n", " "),
        failed_services=snapshot.get("failed_services", ""),
    )

    return {
        **state,
        "raw_logs":       logs,
        "system_snapshot": snapshot,
        "config_files":   configs,
        "project_tree":   project_tree,   # ← injected into Gemini prompts
    }
