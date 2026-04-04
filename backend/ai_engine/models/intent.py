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
        # ── Observation (always safe) ─────────────────────────────
        "read_logs",
        "read_file",
        "read_file_with_lines",
        "list_directory",
        "grep_in_file",
        "grep_in_project",
        "inspect_db",
        "db_query",
        # ── Code editing ─────────────────────────────────────────
        "patch_code_file",
        "write_file",
        "create_model_file",
        "fix_import_path",
        "fix_missing_module",
        # ── Build & dependency management ────────────────────────
        "install_modules",           # npm install / yarn install
        "build_app",                 # npm run build
        # ── Process management ───────────────────────────────────
        "restart_service",
        "pm2_start",
        "kill_process",
        # ── Config / deploy ──────────────────────────────────────
        "edit_config",
        "rename_file",
        "rollback_deploy",
        "redeploy_app",
        # ── Always BLOCKED (demo guardrails) ─────────────────────
        "drop_table",
        "delete_database",
        "exec_arbitrary",
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
