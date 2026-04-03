from fastapi import FastAPI
from pydantic import BaseModel
from graph import agent
import uuid

app = FastAPI()

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
