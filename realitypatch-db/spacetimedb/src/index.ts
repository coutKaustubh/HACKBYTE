import { schema, t, table } from "spacetimedb/server";

// ======================
// TABLES
// ======================

const user = table(
  { name: "user", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    name: t.string(),
    email: t.string(),
  }
);

const project = table(
  { name: "project", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    user_id: t.u64(), // Ref to user.id (mirrors Django user pk)
    django_project_id: t.u64(), // Mirror of the Postgres project PK — used to correlate data
    name: t.string(),
    description: t.string(),
    ssh_key: t.string(),
    server_ip: t.string(),
    root_directory: t.string(),
    deploy_commands: t.string(), // Shell commands to deploy
  }
);

const incident = table(
  { name: "incident", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(),        // Django project PK
    incident_id: t.string(),    // Python string ID e.g. "inc-abc123"
    service: t.string(),
    status: t.string(),         // error / fixing / resolved
    logs_summary: t.string(),   // truncated log snippet
    timestamp: t.timestamp(),
  }
);

const execution = table(
  { name: "execution", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(),
    incident_id: t.string(),    // matches incident.incident_id
    intent_id: t.string(),
    action: t.string(),
    status: t.string(),         // running / success / failed
    output: t.string(),
  }
);

const ai_decision = table(
  { name: "ai_decision", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(),
    incident_id: t.string(),
    error_type: t.string(),
    root_cause: t.string(),
    severity: t.string(),
    num_actions: t.u32(),
  }
);

const safety_check = table(
  { name: "safety_check", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(),
    incident_id: t.string(),
    intent_id: t.string(),
    action: t.string(),
    allowed: t.bool(),
    policy: t.string(),
    reason: t.string(),
  }
);

const agent_event = table(
  { name: "agent_event", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(),       // Django Postgres project PK — correlates events to a project
    incident_id: t.string(),
    event_type: t.string(),
    payload: t.string(),
    timestamp: t.timestamp(),
  }
);

// ======================
// SCHEMA
// ======================

const spacetimedb = schema({
  user,
  project,
  incident,
  execution,
  ai_decision,
  safety_check,
  agent_event,
});

export default spacetimedb;

// ======================
// REDUCERS
// ======================

// Create User
export const create_user = spacetimedb.reducer(
  {
    name: t.string(),
    email: t.string(),
  },
  (ctx, { name, email }) => {
    ctx.db.user.insert({
      id: 0n,
      name,
      email,
    });
  }
);

// Create Project
export const create_project = spacetimedb.reducer(
  {
    user_id: t.u64(),
    django_project_id: t.u64(),
    name: t.string(),
    description: t.string(),
    ssh_key: t.string(),
    server_ip: t.string(),
    root_directory: t.string(),
    deploy_commands: t.string(),
  },
  (ctx, { user_id, django_project_id, name, description, ssh_key, server_ip, root_directory, deploy_commands }) => {
    ctx.db.project.insert({
      id: 0n,
      user_id,
      django_project_id,
      name,
      description,
      ssh_key,
      server_ip,
      root_directory,
      deploy_commands,
    });
  }
);

// Create Incident (called by collect node)
export const create_incident = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
    service: t.string(),
    logs_summary: t.string(),
  },
  (ctx, { project_id, incident_id, service, logs_summary }) => {
    ctx.db.incident.insert({
      id: 0n,
      project_id,
      incident_id,
      service,
      status: "error",
      logs_summary,
      timestamp: ctx.timestamp,
    });
  }
);

// Add AI Decision (called by diagnose node)
export const add_ai_decision = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
    error_type: t.string(),
    root_cause: t.string(),
    severity: t.string(),
    num_actions: t.u32(),
  },
  (ctx, args) => {
    ctx.db.ai_decision.insert({ id: 0n, ...args });
  }
);

// Safety Check (called by enforce node per intent)
export const add_safety_check = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
    intent_id: t.string(),
    action: t.string(),
    allowed: t.bool(),
    policy: t.string(),
    reason: t.string(),
  },
  (ctx, args) => {
    ctx.db.safety_check.insert({ id: 0n, ...args });
  }
);

// Record Execution (called by execute node per action)
export const record_execution = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
    intent_id: t.string(),
    action: t.string(),
    status: t.string(),
    output: t.string(),
  },
  (ctx, args) => {
    ctx.db.execution.insert({ id: 0n, ...args });
  }
);

// Resolve Incident (update status to resolved)
export const resolve_incident = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
  },
  (ctx, { project_id, incident_id }) => {
    // Find the incident by string incident_id
    for (const inc of ctx.db.incident.iter()) {
      if (inc.incident_id === incident_id && inc.project_id === project_id) {
        ctx.db.incident.id.update({ ...inc, status: "resolved" });
        return;
      }
    }
  }
);

// Emit Event for Agent Graph
export const emit_event = spacetimedb.reducer(
  {
    project_id: t.u64(),
    incident_id: t.string(),
    event_type: t.string(),
    payload: t.string(),
  },
  (ctx, { project_id, incident_id, event_type, payload }) => {
    ctx.db.agent_event.insert({
      id: 0n,
      project_id,
      incident_id,
      event_type,
      payload,
      timestamp: ctx.timestamp,
    });
  }
);

// ======================
// INIT
// ======================

export const init = spacetimedb.init((ctx) => {
  // Seed a default user if empty
  const users = ctx.db.user.iter();
  let defaultUserId = 0n;
  
  const userList = Array.from(users);
  if (userList.length === 0) {
    const insertedUser = ctx.db.user.insert({
      id: 0n,
      name: "Admin User",
      email: "admin@realitypatch.ai",
    });
    defaultUserId = insertedUser.id;
  } else {
    defaultUserId = userList[0].id;
  }

  // Seed default projects if empty
  const projects = ctx.db.project.iter();
  const projectList = Array.from(projects);
  if (projectList.length === 0) {
    ctx.db.project.insert({
      id: 0n,
      user_id: defaultUserId,
      django_project_id: 0n,
      name: "E-Commerce Gateway",
      description: "Main API gateway for the e-commerce platform.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/gateway",
      deploy_commands: "npm install && npm run build && npm start",
    });
    ctx.db.project.insert({
      id: 0n,
      user_id: defaultUserId,
      django_project_id: 0n,
      name: "Payment Processor",
      description: "Batch processing and real-time payment verification.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/payments",
      deploy_commands: "npm install && npm run build && npm start",
    });
    ctx.db.project.insert({
      id: 0n,
      user_id: defaultUserId,
      django_project_id: 0n,
      name: "Inventory Sync",
      description: "Warehouse inventory management and tracking.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/inventory",
      deploy_commands: "npm install && npm run build && npm start",
    });
  }
});