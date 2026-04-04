from fastapi import FastAPI
from pydantic import BaseModel
from graph import agent
import os
import uuid
import asyncio
import time
from tools.vm_tools import VMTools
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
    vm = VMTools()
    if not vm.use_ssh:
        print("[Polling] USE_SSH is false. Continuous monitoring on Vultr disabled.")
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
