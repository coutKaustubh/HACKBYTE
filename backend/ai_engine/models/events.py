from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class SpacetimeEvent(BaseModel):
    event_type: Literal[
        "INCIDENT_STARTED",
        "LOGS_COLLECTED",
        "DIAGNOSIS_READY",
        "PLAN_READY",
        "ACTION_ALLOWED",
        "ACTION_BLOCKED",      # triggers red flash + ElevenLabs voice
        "ACTION_EXECUTED",
        "ACTION_FAILED",
        "INCIDENT_RESOLVED",
        "AGENT_THINKING"
    ]
    incident_id: str
    payload: dict
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)
