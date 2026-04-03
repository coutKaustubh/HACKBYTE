import httpx
import os
from models.events import SpacetimeEvent
from dotenv import load_dotenv

load_dotenv()

class SpacetimeTools:
    def __init__(self):
        self.url = os.getenv("SPACETIMEDB_URL")
        self.token = os.getenv("SPACETIMEDB_TOKEN")

    def emit(self, event_type: str, incident_id: str, payload: dict):
        """Push one event to SpacetimeDB"""
        event = SpacetimeEvent(
            event_type=event_type,
            incident_id=incident_id,
            payload=payload
        )
        try:
            # print(f"Mock SpacetimeDB Emit: {event_type} - {incident_id}")
            pass
            # httpx.post(
            #     f"{self.url}/database/call/emit_event",
            #     headers={"Authorization": f"Bearer {self.token}"},
            #     json=event.dict(),
            #     timeout=3.0
            # )
        except Exception as e:
            print(f"SpacetimeDB emit failed: {e}")
            # don't crash the agent if SpacetimeDB is down
