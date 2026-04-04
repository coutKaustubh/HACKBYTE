import time
from tools.vm_tools import VMTools

vm = VMTools()

def verify_node(state: dict) -> dict:
    incident_id = state.get("incident_id", "unknown")
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

    if incident_resolved:
        print(f"✅ [Verify Node] App is {'online in PM2' if pm2_online else ''}{'+ health OK' if health_ok else ''}. Incident resolved!")
    else:
        print(f"❌ [Verify Node] App still not running. PM2: {pm2_out[:200].strip()}")

    return {
        **state,
        "incident_resolved": incident_resolved,
        "retries": retries + 1
    }
