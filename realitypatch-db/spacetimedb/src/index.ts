import { schema, t, table, SenderError } from "spacetimedb/server";

// ======================
// TABLES
// ======================

const incident = table(
  { name: "incident", public: true },
  {
    id: t.u64().primaryKey().autoInc(),
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

// ======================
// SCHEMA
// ======================

const spacetimedb = schema({
  incident,
  execution,
  ai_decision,
  safety_check,
});

export default spacetimedb;

// ======================
// REDUCERS
// ======================

// Create Incident
export const create_incident = spacetimedb.reducer(
  {
    service: t.string(),
    logs: t.string(),
  },
  (ctx, { service, logs }) => {
    ctx.db.incident.insert({
      id:0n,
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
    id : t.u64(),
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

// ======================
// INIT (optional)
// ======================

export const init = spacetimedb.init(() => {});