import os
import uuid
import asyncio
import time
import hashlib

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

from graph import agent
from tools.vm_tools import VMTools, SSHNotConnectedError
from utils.logger import (
    log_ssh_error,
    log_polling_error_detected,
    log_polling_quiet,
    log_polling_same_logs,
    log_polling_agent_done,
    log_build_hook,
)

load_dotenv()

app = FastAPI(title="RealityPatch AI Engine", version="1.0.0")

# ── Polling state ────────────────────────────────────────────────────────────
_last_execution_time  = 0.0
_last_error_signature = ""   # SHA-256 of the full error log from last agent run
_polling_interval     = 30   # seconds


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP: kick off background Vultr monitor
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def start_polling():
    asyncio.create_task(_poll_vultr_logs())


async def _poll_vultr_logs():
    global _last_error_signature, _polling_interval

    # ── Connect fleet ─────────────────────────────────────────────────────────
    from tools.fleet import VMFleet
    fleet = VMFleet()
    fleet.connect_all()

    connected = fleet.connected_vms()
    if not connected:
        # Fall back to single-VM .env config
        try:
            vm = VMTools()
            connected_vms_raw = [vm]
            print("[Monitor] Using single-VM mode (fleet.json has no connected VMs).")
        except SSHNotConnectedError as e:
            log_ssh_error(str(e))
            print("[Monitor] Polling disabled — fix SSH credentials in .env and restart.")
            return
    else:
        # Use VMTools instances from fleet entries
        connected_vms_raw = [e.vm for e in connected]
        print(f"[Monitor] Fleet mode: monitoring {len(connected_vms_raw)} VM(s).")

    # Per-VM error signature tracking
    vm_signatures: dict[int, str] = {}

    while True:
        for idx, vm in enumerate(connected_vms_raw):
            vm_label = getattr(vm, '_vm_id', f'vm-{idx}')
            try:
                errors    = vm._run("journalctl -p err -n 20 --no-pager")
                has_errors = bool(errors and len(errors.strip()) > 10 and "No entries" not in errors)

                if has_errors:
                    sig = hashlib.sha256(errors.encode()).hexdigest()
                    if sig == vm_signatures.get(idx):
                        log_polling_same_logs()
                    else:
                        vm_signatures[idx] = sig
                        _polling_interval   = 5
                        log_polling_error_detected(_polling_interval)

                        initial_state = {
                            "incident_id":  f"inc-{uuid.uuid4().hex[:8]}",
                            "source":       vm_label or "vultr_monitor",
                            "service_hint": "auto-detected",
                        }
                        await run_in_threadpool(agent.invoke, initial_state)
                        _polling_interval = 30
                        log_polling_agent_done(_polling_interval)
                else:
                    _polling_interval = 30
                    log_polling_quiet()

            except Exception as e:
                print(f"  [Monitor Error] {vm_label}: {e}")

        await asyncio.sleep(_polling_interval)


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════════════════════

class TriggerRequest(BaseModel):
    source:       str
    service_hint: str = None

class RunProjectRequest(BaseModel):
    project_id: int          # Django Postgres PK — used to correlate SpacetimeDB events
    source: str = "frontend_trigger"
    service_hint: str = None

class BuildRequest(BaseModel):
    commands: str = None


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cache-stats")
def cache_stats():
    """Gemini API cache hit/miss stats."""
    from utils.cache import diagnosis_cache, patch_cache
    return {
        "diagnosis_cache": diagnosis_cache.stats(),
        "patch_cache":     patch_cache.stats(),
    }


@app.get("/trends")
def trends():
    """Error frequency trends and recurring incident summary."""
    from utils.telemetry import telemetry
    return telemetry.summary()


@app.get("/telemetry/{service}")
def service_telemetry(service: str, limit: int = 20):
    """Full incident history for a specific service."""
    from utils.telemetry import telemetry
    return {
        "service":  service,
        "history":  telemetry.service_history(service, limit=limit),
    }


@app.get("/costs")
def all_costs():
    """Per-incident Gemini API token usage and estimated USD cost."""
    from utils.cost_tracker import cost_tracker
    return {
        "lifetime": cost_tracker.lifetime_total(),
        "incidents": cost_tracker.all_costs(limit=20),
    }


@app.get("/costs/{incident_id}")
def incident_cost(incident_id: str):
    """Token usage and cost for one specific incident run."""
    from utils.cost_tracker import cost_tracker
    return cost_tracker.incident_cost(incident_id)


@app.get("/fleet-status")
def fleet_status():
    """Connection status of all VMs in the monitoring fleet."""
    from tools.fleet import VMFleet
    fleet = VMFleet()
    return {"fleet": fleet.fleet_status()}


@app.get("/tree-stats")
def tree_stats():
    """Project file tree cache status (freshness, file count, age)."""
    from utils.project_tree import tree_cache
    return tree_cache.stats()


@app.post("/tree-refresh")
def tree_refresh():
    """Force an immediate project tree re-fetch from the VM (bypasses TTL)."""
    from utils.project_tree import tree_cache
    tree_cache.invalidate()
    return {"message": "Tree cache invalidated — will re-fetch on next collect cycle."}


@app.post("/trigger-incident")
def trigger_incident(req: TriggerRequest):
    """Manually trigger the full agent pipeline for a given incident source."""
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    result = agent.invoke({
        "incident_id":  incident_id,
        "source":       req.source,
        "service_hint": req.service_hint,
    })
    return {
        "incident_id": incident_id,
        "status":      "completed",
        "resolved":    result.get("incident_resolved"),
        "summary":     result.get("final_summary"),
    }

@app.post("/run-project")
def run_project(req: RunProjectRequest):
    """
    Called by Django when the frontend triggers an agent run for a specific project.
    Injects project_id into the initial state so every SpacetimeDB event is correlated.
    """
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"

    initial_state = {
        "incident_id": incident_id,
        "project_id": req.project_id,
        "source": req.source,
        "service_hint": req.service_hint,
    }

    result = agent.invoke(initial_state)

    return {
        "incident_id": incident_id,
        "project_id": req.project_id,
        "status": "completed",
        "resolved": result.get("incident_resolved"),
        "summary": result.get("final_summary")
    }


@app.post("/run-build")
async def run_build(req: BuildRequest):
    """
    Run user-specified build commands on Vultr, capture logs, feed to AI Agent
    for automatic diagnosis + remediation, then clean up the temp log file.
    """
    try:
        vm = VMTools()
    except SSHNotConnectedError as e:
        log_ssh_error(str(e))
        return JSONResponse(status_code=503, content={"error": str(e)})

    cmd      = req.commands or os.getenv(
        "USER_DEPLOY_COMMANDS",
        "npm install && npm run build > logs/build.log 2>&1 && npm start"
    )
    full_cmd = f"cd {vm.project_root} && mkdir -p logs && {cmd}"
    log_build_hook("Executing commands on Vultr", full_cmd)
    vm._run(full_cmd)

    extracted_logs = vm.read_file("logs/build.log")
    if not extracted_logs.strip() or "No such file" in extracted_logs:
        extracted_logs = "[BuildHook] logs/build.log was empty or not found after running commands."

    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    log_build_hook("Feeding logs to AI Agent", incident_id)

    result = await run_in_threadpool(agent.invoke, {
        "incident_id":  incident_id,
        "source":       "user_build_script",
        "service_hint": "build",
        "custom_logs":  extracted_logs,
    })

    vm._run(f"cd {vm.project_root} && rm -f logs/build.log")
    log_build_hook("Cleaned up logs/build.log")

    return {
        "incident_id": incident_id,
        "status":      "completed",
        "resolved":    result.get("incident_resolved"),
        "summary":     result.get("final_summary"),
    }


@app.get("/export/recent-logs")
def export_recent_logs():
    """Serve local log file contents if LOG_EXPORT_PATH is set."""
    path = os.getenv("LOG_EXPORT_PATH", "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        return data[-200_000:] if len(data) > 200_000 else data
    return (
        "# No LOG_EXPORT_PATH on disk yet.\n"
        "Point LOG_SOURCE_URL to Logtail/Axiom, or set LOG_EXPORT_PATH.\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
