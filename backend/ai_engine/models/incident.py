from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IncidentInput(BaseModel):
    incident_id: str
    source: str                    # e.g. "vultr-vm-prod-01"
    service_hint: Optional[str]    # e.g. "postgresql" — optional

class IncidentState(BaseModel):
    incident_id: str
    source: str
    service_hint: Optional[str] = None

    # filled by collect node
    raw_logs: Optional[str] = None
    system_snapshot: Optional[dict] = None
    config_files: Optional[dict] = None

    # filled by diagnose node
    diagnosis: Optional[dict] = None

    # filled by plan node
    intent_plan: Optional[list] = None

    # filled by enforce node
    enforcement_results: Optional[list] = None

    # filled by execute node
    execution_results: Optional[list] = None
    incident_resolved: Optional[bool] = None
    final_summary: Optional[str] = None
