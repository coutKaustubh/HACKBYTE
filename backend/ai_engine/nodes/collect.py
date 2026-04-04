from tools.vm_tools import VMTools
from tools.spacetime_tools import SpacetimeTools
from tools.log_tools import fetch_deploy_logs

vm = VMTools()
st = SpacetimeTools()

def collect_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    project_id  = state.get("project_id", 0)
    service_hint = state.get("service_hint")

    # ── DEBUG: print the full incoming state ─────────────────────────
    import json
    print("\n" + "="*60)
    print("[DEBUG] collect_node received state:")
    print(json.dumps({
        k: (v[:80] + "...") if isinstance(v, str) and len(v) > 80 else v
        for k, v in state.items()
    }, indent=2, default=str))
    print("="*60 + "\n")

    # ── VALIDATE credentials before doing anything ───────────────────
    ssh_key    = state.get("ssh_key", "").strip()
    server_ip  = state.get("server_ip", "").strip()
    root_dir   = state.get("root_dir", "").strip()

    import re
    valid_ip = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", server_ip)

    if not server_ip or not valid_ip:
        raise ValueError(
            f"[Agent] Invalid server IP: '{server_ip}'. "
            "Please update your project with a valid IPv4 address (e.g. 192.168.1.1)."
        )
    if not ssh_key or len(ssh_key) < 20:
        raise ValueError(
            f"[Agent] SSH key looks invalid (too short or empty). "
            "Please paste your full private SSH key in the project settings."
        )
    if not root_dir:
        raise ValueError("[Agent] root_dir is not set. Set the project root directory (e.g. /root/app).")


    # print("INCIDENT_STARTED", incident_id, {"source": state["source"]})
    st.emit("INCIDENT_STARTED", incident_id, {
        "source": state.get("source", "unknown"),
        "project_id": project_id,
    }, project_id=project_id)

    # ── Domain table: create an incident record ───────────────────────
    st.create_incident(
        project_id=project_id,
        incident_id=incident_id,
        service=service_hint or "auto-detected",
        logs_summary="Collecting logs..."
    )

    # collect system snapshot (includes pm2_status now)
    snapshot = vm.get_system_snapshot()
    configs  = vm.get_config_files()

    # ── Primary: Pull PM2 logs (the real app logs) ─────────────────
    pm2_logs = vm._run("pm2 logs --nostream --lines 100 2>/dev/null || pm2 logs --lines 100 2>&1 | head -200")
    pm2_status_full = vm._run("pm2 status --no-color 2>/dev/null")

    logs = f"=== PM2 Status ===\n{pm2_status_full}\n\n=== PM2 App Logs (last 100 lines) ===\n{pm2_logs}"

    # ── Secondary: systemd service logs if a specific service is hinted ──
    if service_hint and service_hint not in ("auto-detected", "build"):
        svc_logs = vm.read_service_logs(service_hint, lines=100)
        logs += f"\n\n=== {service_hint} (journalctl) ===\n{svc_logs}"

    # ── External log source (Logtail / Axiom etc.) ──────────────────
    external = fetch_deploy_logs()
    if external:
        logs = (
            "=== Deploy / app logs (LOG_SOURCE_URL) ===\n"
            f"{external}\n\n"
            f"{logs}"
        )

    # ── Custom logs from /run-build endpoint ────────────────────────
    custom_logs = state.get("custom_logs", "")
    if custom_logs:
        logs = (
            "=== Custom Build Logs ===\n"
            f"{custom_logs}\n\n"
            f"{logs}"
        )

    # ── Emit: logs collected ─────────────────────────────────────────
    # print("LOGS_COLLECTED" , incident_id, {
    #     "project_id": project_id,
    #     "log_length": len(logs),
    #     "pm2_status_snippet": pm2_status_full[:120].replace("\n", " "),
    #     "failed_services": snapshot.get("failed_services", ""),
    # }, project_id=project_id)
    st.emit("LOGS_COLLECTED", incident_id, {
        "project_id": project_id,
        "log_length": len(logs),
        "pm2_status_snippet": pm2_status_full[:120].replace("\n", " "),
        "failed_services": snapshot.get("failed_services", ""),
    }, project_id=project_id)

    return {
        **state,
        "project_id": project_id,
        "raw_logs": logs,
        "system_snapshot": snapshot,
        "config_files": configs
    }
