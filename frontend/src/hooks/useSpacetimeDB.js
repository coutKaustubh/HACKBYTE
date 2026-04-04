import { useState, useEffect, useCallback } from 'react';
import { DbConnection, reducers } from '../module_bindings';

export function useSpacetimeDB() {
  const [incidents, setIncidents] = useState({});
  const [executions, setExecutions] = useState({});
  const [aiDecisions, setAiDecisions] = useState({});
  const [safetyChecks, setSafetyChecks] = useState({});
  const [agentEvents, setAgentEvents] = useState({});
  const [users, setUsers] = useState({});
  const [projects, setProjects] = useState({});
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let conn;

    const connectToDB = () => {
      // Connect to the local SpacetimeDB instance
      conn = DbConnection.builder()
        .withUri("http://127.0.0.1:3000") // SpacetimeDB client will manage the WS protocol over this URI
        .withDatabaseName("realitypatch-db-2lsay")
        .build();

      conn.onConnect((context) => {
        setIsConnected(true);
        console.log("Connected to SpacetimeDB!");

        conn.subscriptionBuilder()
          .onApplied((ctx) => {
             // Fetch all rows natively from the client cache on initial sync
             const allIncidents = conn.db.incident.iter();
             const allExecutions = conn.db.execution.iter();
             const allAiDecisions = conn.db.ai_decision.iter();
             const allSafetyChecks = conn.db.safety_check.iter();
             const allAgentEvents = conn.db.agent_event.iter();
             const allUsers = conn.db.user.iter();
             const allProjects = conn.db.project.iter();

             const incMap = {};
             for (let inc of allIncidents) { incMap[inc.id] = inc; }
             setIncidents(incMap);

             const execMap = {};
             for (let ex of allExecutions) { execMap[ex.incidentId] = ex; }
             setExecutions(execMap);

             const aiMap = {};
             for (let ai of allAiDecisions) { aiMap[ai.incidentId] = ai; }
             setAiDecisions(aiMap);

             const safetyMap = {};
             for (let safe of allSafetyChecks) { safetyMap[safe.incidentId] = safe; }
             setSafetyChecks(safetyMap);

             const agentEventMap = {};
             for (let ae of allAgentEvents) { agentEventMap[ae.id] = ae; }
             setAgentEvents(agentEventMap);

             const userMap = {};
             for (let u of allUsers) { userMap[u.id] = u; }
             setUsers(userMap);

             const projectMap = {};
             for (let p of allProjects) { projectMap[p.id] = p; }
             setProjects(projectMap);
          })
          .subscribe([
            "SELECT * FROM incident",
            "SELECT * FROM execution",
            "SELECT * FROM ai_decision",
            "SELECT * FROM safety_check",
            "SELECT * FROM agent_event",
            "SELECT * FROM user",
            "SELECT * FROM project"
          ]);
      });

      // Hook up live dynamic updates
      conn.db.incident.onInsert((ctx, row) => {
         setIncidents(prev => ({ ...prev, [row.id]: row }));
      });
      conn.db.execution.onInsert((ctx, row) => {
         setExecutions(prev => ({ ...prev, [row.incidentId]: row }));
      });
      conn.db.ai_decision.onInsert((ctx, row) => {
         setAiDecisions(prev => ({ ...prev, [row.incidentId]: row }));
      });
      conn.db.safety_check.onInsert((ctx, row) => {
         setSafetyChecks(prev => ({ ...prev, [row.incidentId]: row }));
      });
      conn.db.agent_event.onInsert((ctx, row) => {
         setAgentEvents(prev => ({ ...prev, [row.id]: row }));
      });
      conn.db.user.onInsert((ctx, row) => {
         setUsers(prev => ({ ...prev, [row.id]: row }));
      });
      conn.db.project.onInsert((ctx, row) => {
         setProjects(prev => ({ ...prev, [row.id]: row }));
      });
      
      // Handle updates if an incident resolves
      conn.db.incident.onUpdate((ctx, oldRow, newRow) => {
         setIncidents(prev => ({ ...prev, [newRow.id]: newRow }));
      });
      conn.db.execution.onUpdate((ctx, oldRow, newRow) => {
         setExecutions(prev => ({ ...prev, [newRow.incidentId]: newRow }));
      });

      conn.onDisconnect(() => {
        setIsConnected(false);
        console.log("Disconnected. Reconnecting...");
        setTimeout(connectToDB, 3000);
      });
    };

    connectToDB();

    return () => {
      if (conn) conn.disconnect();
    };
  }, []);

  const createIncident = useCallback((projectId, service, logs) => {
    reducers.createIncident(projectId, service, logs);
  }, []);

  const startExecution = useCallback((incidentId) => {
    reducers.startExecution(incidentId);
  }, []);

  const createProject = useCallback((userId, name, description, sshKey, serverIp, rootDirectory) => {
    reducers.createProject(userId, name, description, sshKey, serverIp, rootDirectory);
  }, []);

  const resolveIncident = useCallback((incidentId) => {
    reducers.resolveIncident(incidentId);
  }, []);

  return {
    isConnected,
    incidents,
    executions,
    aiDecisions,
    safetyChecks,
    agentEvents,
    users,
    projects,
    createIncident,
    createProject,
    startExecution,
    resolveIncident,
  };
}
