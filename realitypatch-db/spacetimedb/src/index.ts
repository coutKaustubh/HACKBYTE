import { schema, t, table, SenderError } from "spacetimedb/server";

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
    user_id: t.u64(), // Ref to user.id
    name: t.string(),
    description: t.string(),
    ssh_key: t.string(),
    server_ip: t.string(),
    root_directory: t.string(),
  }
);

const incident = table(
  { name: "incident", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    project_id: t.u64(), // Ref to project.id
    service: t.string(),
    status: t.string(), // error / fixing / resolved
    logs: t.string(),
    timestamp: t.timestamp(),
  }
);

const execution = table(
  { name: "execution", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    incident_id: t.u64(),
    status: t.string(), // running / success / failed
    output: t.string(),
  }
);

const ai_decision = table(
  { name: "ai_decision", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    incident_id: t.u64(),
    analysis: t.string(),
    command: t.string(),
    confidence: t.f64(),
  }
);

const safety_check = table(
  { name: "safety_check", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    incident_id: t.u64(),
    allowed: t.bool(),
    reason: t.string(),
  }
);

const agent_event = table(
  { name: "agent_event", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
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
    name: t.string(),
    description: t.string(),
    ssh_key: t.string(),
    server_ip: t.string(),
    root_directory: t.string(),
  },
  (ctx, { user_id, name, description, ssh_key, server_ip, root_directory }) => {
    ctx.db.project.insert({
      id: 0n,
      user_id,
      name,
      description,
      ssh_key,
      server_ip,
      root_directory,
    });
  }
);

// Create Incident
export const create_incident = spacetimedb.reducer(
  {
    project_id: t.u64(),
    service: t.string(),
    logs: t.string(),
  },
  (ctx, { project_id, service, logs }) => {
    ctx.db.incident.insert({
      id: 0n,
      project_id,
      service,
      status: "error",
      logs,
      timestamp: ctx.timestamp,
    });
  }
);

// Add AI Decision
export const add_ai_decision = spacetimedb.reducer(
  {
    id: t.u64(),
    incident_id: t.u64(),
    analysis: t.string(),
    command: t.string(),
    confidence: t.f64(),
  },
  (ctx, args) => {
    ctx.db.ai_decision.insert(args);
  }
);

// Safety Check
export const add_safety_check = spacetimedb.reducer(
  {
    id: t.u64(),
    incident_id: t.u64(),
    allowed: t.bool(),
    reason: t.string(),
  },
  (ctx, args) => {
    ctx.db.safety_check.insert(args);
  }
);

// Start Execution
export const start_execution = spacetimedb.reducer(
  {
    incident_id: t.u64(),
  },
  (ctx, { incident_id }) => {
    ctx.db.execution.insert({
      id: 0n,
      incident_id,
      status: "running",
      output: "",
    });
  }
);

// Resolve Incident
export const resolve_incident = spacetimedb.reducer(
  {
    incident_id: t.u64(),
  },
  (ctx, { incident_id }) => {
    const inc = ctx.db.incident.id.find(incident_id);
    if (!inc) {
      throw new SenderError("Incident not found");
    }

    ctx.db.incident.id.update({
      ...inc,
      status: "resolved",
    });
  }
);

// Emit Event for Agent Graph
export const emit_event = spacetimedb.reducer(
  {
    incident_id: t.string(),
    event_type: t.string(),
    payload: t.string(),
  },
  (ctx, { incident_id, event_type, payload }) => {
    ctx.db.agent_event.insert({
      id: 0n,
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
      name: "E-Commerce Gateway",
      description: "Main API gateway for the e-commerce platform.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/gateway",
    });
    ctx.db.project.insert({
      id: 0n,
      user_id: defaultUserId,
      name: "Payment Processor",
      description: "Batch processing and real-time payment verification.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/payments",
    });
    ctx.db.project.insert({
      id: 0n,
      user_id: defaultUserId,
      name: "Inventory Sync",
      description: "Warehouse inventory management and tracking.",
      ssh_key: "default-key",
      server_ip: "127.0.0.1",
      root_directory: "/app/inventory",
    });
  }
});