import time
from tools.vm_tools import VMTools
from tools.spacetime_tools import SpacetimeTools

vm = VMTools()
st = SpacetimeTools()

def verify_node(state: dict) -> dict:
    incident_id = state.get("incident_id", "unknown")
    project_id  = state.get("project_id", 0)
    retries = state.get("retries", 0)

    print(f"\n🔄 [Verify Node] Attempting verification after pass {retries + 1}...")

    # Give PM2 time to fully boot the process
    time.sleep(8)

    # ── Primary check: Is the app running in PM2? ──────────────────
    pm2_out = vm._run("pm2 status --no-color 2>/dev/null")
    pm2_online = "online" in pm2_out.lower()

    # ── Secondary check: HTTP health endpoint (if configured) ──────
    health_ok = False
    try:
        import httpx
        if vm.app_url and "your-app" not in vm.app_url:
            resp = httpx.get(f"{vm.app_url}/health", timeout=8.0)
            health_ok = resp.status_code < 500
    except Exception:
        health_ok = False  # not required — pm2 check is enough

    # Consider resolved if PM2 shows online OR health endpoint responds
    incident_resolved = pm2_online or health_ok

    status_msg = (
        "RESOLVED — app is online" if incident_resolved
        else f"STILL_DOWN — retry {retries + 1}"
    )

    # ── Emit: verification result ──────────────────────────────────
    print("INCIDENT_RESOLVED" if incident_resolved else "LOGS_COLLECTED", incident_id, {
        "project_id": project_id,
        "verify_pass": retries + 1,
        "pm2_online": pm2_online,
        "health_ok": health_ok,
        "status": status_msg,
    })
    st.emit("INCIDENT_RESOLVED" if incident_resolved else "LOGS_COLLECTED", incident_id, {
        "project_id": project_id,
        "verify_pass": retries + 1,
        "pm2_online": pm2_online,
        "health_ok": health_ok,
        "status": status_msg,
    }, project_id=project_id)

    return {
        **state,
        "project_id": project_id,
        "incident_resolved": incident_resolved,
        "retries": retries + 1
    }
