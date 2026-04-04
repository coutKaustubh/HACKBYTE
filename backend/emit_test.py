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
    print(f"  URL:     {st.url}")
    print(f"  DB Name: {st.db_name}")
    print(f"  Token:   {'[PRESENT]' if st.token else '[NOT SET]'}\n")
    
    incident_id = "test-incident-999"
    project_id  = 6   # matches the 'new' project (django_project_id=6) in SpacetimeDB
    
    # 1. INCIDENT_STARTED
    print(">> Emitting INCIDENT_STARTED...")
    st.emit("INCIDENT_STARTED", incident_id, {
        "source": "emit_test",
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)
    
    # 2. LOGS_COLLECTED
    print(">> Emitting LOGS_COLLECTED...")
    st.emit("LOGS_COLLECTED", incident_id, {
        "log_length": 1054,
        "failed_services": "postgresql, nginx",
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)
    
    # 3. AGENT_THINKING
    print(">> Emitting AGENT_THINKING...")
    st.emit("AGENT_THINKING", incident_id, {
        "chunk": "Checking postgresql logs... found connection error.",
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)

    # 4. DIAGNOSIS_READY
    print(">> Emitting DIAGNOSIS_READY...")
    st.emit("DIAGNOSIS_READY", incident_id, {
        "error_type": "DB_CONNECTION_FAILURE",
        "root_cause": "PostgreSQL not accepting connections on port 5432",
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)

    # 5. PLAN_READY
    print(">> Emitting PLAN_READY...")
    st.emit("PLAN_READY", incident_id, {
        "total_intents": 2,
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)

    # 6. ACTION_BLOCKED (demo)
    print(">> Emitting ACTION_BLOCKED...")
    st.emit("ACTION_BLOCKED", incident_id, {
        "intent_id": "int-test-001",
        "action": "drop_table",
        "reason": "Blocked by policy P-001",
        "project_id": project_id,
    }, project_id=project_id)
    time.sleep(0.5)

    # 7. INCIDENT_RESOLVED
    print(">> Emitting INCIDENT_RESOLVED...")
    st.emit("INCIDENT_RESOLVED", incident_id, {
        "actions_allowed": 1,
        "actions_blocked": 1,
        "actions_succeeded": 1,
        "project_id": project_id,
        "summary": "Test incident resolved successfully.",
    }, project_id=project_id)
    time.sleep(0.5)

    # ── Domain table writes ────────────────────────────────────────────
    print("\n>> Writing to domain tables...")

    print(">> create_incident...")
    st.create_incident(
        project_id=project_id,
        incident_id=incident_id,
        service="test-service",
        logs_summary="PM2 logs show connection refused on port 5432"
    )

    print(">> add_ai_decision...")
    st.add_ai_decision(
        project_id=project_id,
        incident_id=incident_id,
        error_type="DB_CONNECTION_FAILURE",
        root_cause="PostgreSQL not accepting connections on port 5432",
        severity="high",
        num_actions=2,
    )

    print(">> add_safety_check (allowed)...")
    st.add_safety_check(
        project_id=project_id,
        incident_id=incident_id,
        intent_id=f"int-{incident_id}-001",
        action="restart_service",
        allowed=True,
        policy="P-002",
        reason="Service restart is permitted",
    )

    print(">> add_safety_check (blocked)...")
    st.add_safety_check(
        project_id=project_id,
        incident_id=incident_id,
        intent_id=f"int-{incident_id}-demo-block",
        action="drop_table",
        allowed=False,
        policy="P-001",
        reason="Destructive DB operations are blocked",
    )

    print(">> record_execution...")
    st.record_execution(
        project_id=project_id,
        incident_id=incident_id,
        intent_id=f"int-{incident_id}-001",
        action="restart_service",
        status="success",
        output="Service restarted successfully. PM2 shows online.",
    )

    print(">> resolve_incident...")
    st.resolve_incident(project_id=project_id, incident_id=incident_id)

    print("\n✅ All events + domain table writes done!")
    print("Verify with:")
    print('  spacetime sql --server local realitypatch-db-2lsay "SELECT * FROM agent_event"')
    print('  spacetime sql --server local realitypatch-db-2lsay "SELECT * FROM incident"')
    print('  spacetime sql --server local realitypatch-db-2lsay "SELECT * FROM ai_decision"')
    print('  spacetime sql --server local realitypatch-db-2lsay "SELECT * FROM safety_check"')
    print('  spacetime sql --server local realitypatch-db-2lsay "SELECT * FROM execution"')

if __name__ == "__main__":
    run_test()
