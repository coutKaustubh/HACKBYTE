import httpx
import os
from models.events import SpacetimeEvent
import json
from dotenv import load_dotenv

load_dotenv()

class SpacetimeTools:
    def __init__(self):
        self.url = os.getenv("SPACETIMEDB_URL", "http://localhost:3000")
        self.token = os.getenv("SPACETIMEDB_TOKEN", "")
        self.db_name = os.getenv("SPACETIMEDB_DB_NAME", "realitypatch-db")

    def emit(self, event_type: str, incident_id: str, payload: dict):
        """Push one event to SpacetimeDB"""
        event = SpacetimeEvent(
            event_type=event_type,
            incident_id=incident_id,
            payload=payload
        )
        try:
            print(f"SpacetimeDB Emit: {event_type} - {incident_id}")
            
            args_payload = {
                "args": [
                    incident_id,
                    event_type,
                    json.dumps(payload)
                ]
            }

            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            print(f"Payload: {json.dumps(payload, indent=2)}")
            # httpx.post(
            #     f"{self.url}/v1/database/{self.db_name}/call/emit_event",
            #     headers=headers,
            #     json=args_payload,
            #     timeout=3.0
            # )
        except Exception as e:
            print(f"SpacetimeDB emit failed: {e}")
            # don't crash the agent if SpacetimeDB is down
