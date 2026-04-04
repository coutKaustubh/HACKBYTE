from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from graph import agent
import os
import uuid
import asyncio
import time
from tools.vm_tools import VMTools, SSHNotConnectedError
from starlette.concurrency import run_in_threadpool

app = FastAPI()

last_execution_time = 0
last_error_signature = ""
polling_interval = 30 # standard 30 secs

@app.on_event("startup")
async def start_polling():
    asyncio.create_task(poll_vultr_logs())

async def poll_vultr_logs():
    global last_execution_time, last_error_signature, polling_interval
    try:
        vm = VMTools()  # raises SSHNotConnectedError if SSH fails
    except SSHNotConnectedError as e:
        print(f"\n🚨 [Polling] FATAL — {e}")
        print("[Polling] Monitoring disabled. Fix SSH config in .env and restart.")
        return

    print("[Polling] Started background monitor for Vultr server logs (journalctl)...")
    while True:
        try:
            errors = vm._run("journalctl -p err -n 20 --no-pager")
            
            # Simple check to see if we have real errors avoiding empty string
            if errors and len(errors.strip()) > 10 and "No entries" not in errors:
                current_time = time.time()
                
                # We need a signature so we don't trigger on the EXACT same error stream indefinitely
                current_sig = hash(errors[-200:])
                
                # Check stabilization window: at least 60 seconds between executions
                if current_time - last_execution_time > 60 and current_sig != last_error_signature:
                    print(f"\n🚨 [Polling] Detected new server errors! Interval changed to {polling_interval}s. Waking up Agent! 🚨")
                    last_execution_time = current_time
                    last_error_signature = current_sig
                    
                    # Phase change: fast feedback
                    polling_interval = 5
                    
                    # Execute agent
                    initial_state = {
                        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
                        "source": "vultr_continuous_monitor",
                        "service_hint": "auto-detected"
                    }
                    
                    await run_in_threadpool(agent.invoke, initial_state)
                    
                    print(f"[Polling] Agent finished. Entering stabilization phase (15s).")
                    polling_interval = 15 # Stabilization
                else:
                    if current_time - last_execution_time > 120:
                        polling_interval = 30 # back to long-running monitoring
            else:
                # No errors
                polling_interval = 30
                
        except Exception as e:
            print(f"[Polling Error] {e}")
            
        await asyncio.sleep(polling_interval)

class TriggerRequest(BaseModel):
    source: str
    service_hint: str = None

class RunProjectRequest(BaseModel):
    project_id: int          # Django Postgres PK — used to correlate SpacetimeDB events
    source: str = "frontend_trigger"
    service_hint: str = None

class BuildRequest(BaseModel):
    commands: str = None

@app.post("/trigger-incident")
def trigger_incident(req: TriggerRequest):
    """
    Sharad calls this when a fault is detected.
    Returns immediately — agent runs in background.
    """
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"

    initial_state = {
        "incident_id": incident_id,
        "source": req.source,
        "service_hint": req.service_hint
    }

    # run the full LangGraph pipeline
    result = agent.invoke(initial_state)

    return {
        "incident_id": incident_id,
        "status": "completed",
        "resolved": result.get("incident_resolved"),
        "summary": result.get("final_summary")
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
    Executes specified deployment commands, saving logs to a temporary file.
    Feeds the logs to the AI Agent to detect issues and remediate, then cleans up.
    """
    try:
        vm = VMTools()
    except SSHNotConnectedError as e:
        return JSONResponse(status_code=503, content={"error": str(e)})

    cmd = req.commands or os.getenv("USER_DEPLOY_COMMANDS", "npm install && npm run build > logs/build.log 2>&1 && npm start")
    full_cmd = f"cd {vm.project_root} && mkdir -p logs && {cmd}"
    print(f"[BuildHook] Executing: {full_cmd}")
    vm._run(full_cmd)

    extracted_logs = vm.read_file("logs/build.log")
    if not extracted_logs.strip() or "No such file" in extracted_logs:
        extracted_logs = "[BuildHook] logs/build.log was empty or not found after running commands."

    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    initial_state = {
        "incident_id": incident_id,
        "source": "user_build_script",
        "service_hint": "build",
        "custom_logs": extracted_logs
    }

    print(f"[BuildHook] Feeding logs to Agent ({incident_id})")
    result = await run_in_threadpool(agent.invoke, initial_state)

    vm._run(f"cd {vm.project_root} && rm -f logs/build.log")
    print(f"[BuildHook] Cleaned up temporary logs/build.log")

    return {
        "incident_id": incident_id,
        "status": "completed",
        "resolved": result.get("incident_resolved"),
        "summary": result.get("final_summary")
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/export/recent-logs")
def export_recent_logs():
    """
    Optional log source for LOG_SOURCE_URL: same base URL + /export/recent-logs
    Set LOG_EXPORT_PATH to a file the app writes (e.g. request logs); otherwise returns a short hint.
    """
    path = os.getenv("LOG_EXPORT_PATH", "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        return data[-200000:] if len(data) > 200000 else data
    return (
        "# No LOG_EXPORT_PATH on disk yet. "
        "Point LOG_SOURCE_URL to Logtail/Axiom, or set LOG_EXPORT_PATH after writing logs to a file.\n"
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
