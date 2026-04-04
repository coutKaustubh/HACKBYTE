import httpx
import os
import json
from pathlib import Path
from models.events import SpacetimeEvent
from dotenv import load_dotenv

_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV)

class SpacetimeTools:
    def __init__(self):
        self.url = os.getenv("SPACETIMEDB_URL", "http://localhost:3000")
        self.token = os.getenv("SPACETIMEDB_TOKEN", "")
        self.db_name = os.getenv("SPACETIMEDB_DB_NAME", "realitypatch-db")

    def _call(self, reducer: str, args: dict):
        """Internal: call any SpacetimeDB reducer with named args."""
        try:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = httpx.post(
                f"{self.url}/v1/database/{self.db_name}/call/{reducer}",
                headers=headers,
                json=args,
                timeout=3.0
            )
            if response.status_code not in (200, 204):
                print(f"[SpacetimeDB] /{reducer} → {response.status_code}: {response.text[:200]}")
        except httpx.ConnectError:
            print(f"[SpacetimeDB] Cannot connect to {self.url} — is SpacetimeDB running?")
        except Exception as e:
            print(f"[SpacetimeDB] /{reducer} failed: {e}")

    # ── Generic event stream ─────────────────────────────────────────────────

    def emit(self, event_type: str, incident_id: str, payload: dict, project_id: int = 0):
        """Push a generic event to agent_event table (used for the live feed)."""
        SpacetimeEvent(event_type=event_type, incident_id=incident_id, payload=payload)  # validate
        print(f"[SpacetimeDB] {event_type} | incident={incident_id} | project={project_id}")
        self._call("emit_event", {
            "project_id": project_id,
            "incident_id": incident_id,
            "event_type": event_type,
            "payload": json.dumps(payload),
        })

    # ── Domain-specific table writes ─────────────────────────────────────────

    def create_incident(self, project_id: int, incident_id: str, service: str, logs_summary: str):
        """Write to the incident table when the pipeline starts."""
        print(f"[SpacetimeDB] create_incident | incident={incident_id} | project={project_id}")
        self._call("create_incident", {
            "project_id": project_id,
            "incident_id": incident_id,
            "service": service,
            "logs_summary": logs_summary[:500],  # keep it compact
        })

    def add_ai_decision(self, project_id: int, incident_id: str, error_type: str,
                        root_cause: str, severity: str, num_actions: int):
        """Write AI diagnosis result to ai_decision table."""
        print(f"[SpacetimeDB] add_ai_decision | incident={incident_id} | error={error_type}")
        self._call("add_ai_decision", {
            "project_id": project_id,
            "incident_id": incident_id,
            "error_type": error_type,
            "root_cause": root_cause,
            "severity": severity,
            "num_actions": num_actions,
        })

    def add_safety_check(self, project_id: int, incident_id: str, intent_id: str,
                         action: str, allowed: bool, policy: str, reason: str):
        """Write ArmorClaw's verdict to safety_check table."""
        print(f"[SpacetimeDB] safety_check | intent={intent_id} | allowed={allowed}")
        self._call("add_safety_check", {
            "project_id": project_id,
            "incident_id": incident_id,
            "intent_id": intent_id,
            "action": action,
            "allowed": allowed,
            "policy": policy,
            "reason": reason,
        })

    def record_execution(self, project_id: int, incident_id: str, intent_id: str,
                         action: str, status: str, output: str):
        """Write execution result to execution table."""
        print(f"[SpacetimeDB] record_execution | intent={intent_id} | status={status}")
        self._call("record_execution", {
            "project_id": project_id,
            "incident_id": incident_id,
            "intent_id": intent_id,
            "action": action,
            "status": status,
            "output": output[:1000],  # trim large outputs
        })

    def resolve_incident(self, project_id: int, incident_id: str):
        """Mark incident as resolved in the incident table."""
        print(f"[SpacetimeDB] resolve_incident | incident={incident_id} | project={project_id}")
        self._call("resolve_incident", {
            "project_id": project_id,
            "incident_id": incident_id,
        })
