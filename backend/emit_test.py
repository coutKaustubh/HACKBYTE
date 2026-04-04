import sys
import os
import time

# Make sure python can find the ai_engine modules
sys.path.append(os.path.join(os.path.dirname(__file__), "ai_engine"))

from tools.spacetime_tools import SpacetimeTools

def run_test():
    print("Initializing SpacetimeTools...")
    st = SpacetimeTools()
    
    # Verify environment values
    print("Target DB Settings:")
    print(f" - URL: {st.url}")
    print(f" - DB Name: {st.db_name}")
    print(f" - Token: {'[PRESENT]' if st.token else '[NOT SET]'}\n")
    
    incident_id = "test-incident-999"
    
    # 1. INCIDENT_STARTED
    print(">> Emitting INCIDENT_STARTED...")
    st.emit("INCIDENT_STARTED", incident_id, {"source": "vultr-vm-prod-01"})
    time.sleep(1)
    
    # 2. LOGS_COLLECTED
    print(">> Emitting LOGS_COLLECTED...")
    st.emit("LOGS_COLLECTED", incident_id, {
        "log_length": 1054,
        "failed_services": "postgresql, nginx"
    })
    time.sleep(1)
    
    # 3. AGENT_THINKING
    print(">> Emitting AGENT_THINKING...")
    st.emit("AGENT_THINKING", incident_id, {"chunk": "Checking postgresql logs... found connection error."})
    time.sleep(1)
    
    print("\nTest complete!")
    print("You can verify the events in your SpacetimeDB console by querying the 'agent_event' table.")

if __name__ == "__main__":
    run_test()
