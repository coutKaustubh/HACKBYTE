from tools.vm_tools import VMTools
from tools.spacetime_tools import SpacetimeTools
from tools.log_tools import fetch_deploy_logs

vm = VMTools()
st = SpacetimeTools()

def collect_node(state: dict) -> dict:
    incident_id = state["incident_id"]
    service_hint = state.get("service_hint")

    st.emit("INCIDENT_STARTED", incident_id, {"source": state["source"]})

    # collect everything in parallel mentally — run all commands
    snapshot = vm.get_system_snapshot()
    configs  = vm.get_config_files()

    # if we know which service is broken, grab its logs specifically
    if service_hint:
        logs = vm.read_service_logs(service_hint, lines=150)
    else:
        # grab logs from all common services
        logs = "\n\n".join([
            f"=== postgresql ===\n{vm.read_service_logs('postgresql', 80)}",
            f"=== nginx ===\n{vm.read_service_logs('nginx', 50)}",
            f"=== redis ===\n{vm.read_service_logs('redis', 50)}",
        ])

    external = fetch_deploy_logs()
    if external:
        logs = (
            "=== Deploy / app logs (LOG_SOURCE_URL) ===\n"
            f"{external}\n\n"
            "=== Host / service context (SSH or simulation) ===\n"
            f"{logs}"
        )

    st.emit("LOGS_COLLECTED", incident_id, {
        "log_length": len(logs),
        "failed_services": snapshot.get("failed_services", "")
    })

    return {
        **state,
        "raw_logs": logs,
        "system_snapshot": snapshot,
        "config_files": configs
    }
