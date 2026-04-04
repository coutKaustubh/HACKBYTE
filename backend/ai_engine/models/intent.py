from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class Intent(BaseModel):
    intent_id: str
    incident_id: str
    step: int
    agent: str = "patch-proposer-agent"
    
    # the action — ArmorClaw checks this against policies
    action: Literal[
        "restart_service",
        "edit_config",
        "rollback_deploy",
        "redeploy_app",
        "read_logs",
        "read_file",
        "write_file",
        "drop_table",        # will always be BLOCKED — demo purpose
        "delete_database",   # will always be BLOCKED
        "exec_arbitrary"     # will always be BLOCKED
    ]
    
    target: str              # service name or file path
    params: dict = {}        # extra args e.g. {"max_connections": 200}
    reason: str              # why this action is needed
    risk_level: Literal["low", "medium", "high", "critical"]
    reversible: bool
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)

class EnforcementResult(BaseModel):
    intent_id: str
    action: str
    decision: Literal["ALLOWED", "BLOCKED"]
    policy_matched: str
    reason: str
    token: Optional[str] = None   # only present if ALLOWED
