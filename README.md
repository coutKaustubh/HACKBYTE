# 🌌 XOne

> **A Production-Grade AI-Driven Infrastructure Auto-Remediation System**

---

## 📖 Overview

**XOne** is an intelligent, self-healing infrastructure system designed to monitor, detect, and automatically resolve server and application errors in real-time. 

Unlike traditional AI pipelines that blindly execute generated scripts, XOne implements **The Reality Filter** (via OPEN CLAW / armoriq)—a rigorous secondary safety net ensuring that AI-proposed solutions are technically sound, strictly relevant, and entirely non-destructive.

---

## ⚙️ How It Works (The Core Flow)

The system operates on a highly secure, autonomous loop:

1. **Continuous Monitoring:** A monitoring agent actively observes server/application logs in real-time.
2. **Anomaly Detection:** When an error occurs, the context (last N lines of logs) is extracted and packaged into a structured JSON payload.
3. **Primary Diagnosis (Gemini AI):** The log data is analyzed by the first AI layer. It generates *multiple* potential fixes and their reasoning, returning the output as structured JSON.
4. **The Reality Filter (OPEN CLAW / armoriq):** A secondary validation AI evaluates every proposed solution. It aggressively filters out hallucinated, unsafe, or destructive commands, returning a definitive list of approved vs. rejected solutions.
5. **Decision & Execution:** Only verified, approved actions are selected and executed on the target system.
6. **Real-Time Feedback:** Execution results are captured, the system state is updated, and the full timeline is synced to the frontend.

> **CORE PRINCIPLE:** The system NEVER blindly trusts AI. It verifies AI-generated actions before execution. This ensures that only real, safe, and meaningful actions affect your infrastructure.

---

## 🏗️ Architecture

The system is separated into distinct, scalable layers:

### 1. Frontend Dashboard (React)
- Live monitoring dashboard displaying projects, system health, and AI actions.
- Real-time event updates delivered instantly via WebSockets.

### 2. Backend Orchestrator (Django + Django REST Framework)
- Handles user authentication (Google/GitHub integration).
- Manages User ↔ Project mapping and role-based access.
- Coordinates the complex AI processing pipeline and task delegations.

### 3. Task Queue (Redis + Celery)
- Offloads heavy asynchronous workloads such as log crunching, AI network calls, and infrastructure execution commands.

### 4. Infrastructure & Hosting
- Fully containerized microservices via **Docker**.
- High-performance deployment hosted on **Vultr**.

---

## 💾 Data Strategy

Our system strictly separates persistent business logic from high-velocity operational telemetry.

### 🟢 PostgreSQL (Stable Relational Data)
Powered by Django's ORM, Postgres holds our core configurations:
- **Users**: (`id`, `name`, `email`, Google/GitHub auth providers)
- **Projects**: (`name`, `server IP & details`, `status`, linked user)
- **Configurations**: What logs to monitor, AI settings, and error thresholds
- **Permissions**: Access control and (optional) team management
- **Metadata**: Stable statistics like project creation timestamps and last deployments

### ⚡ SpacetimeDB / Real-Time Database (High-Velocity State)
Our real-time engine stores transient, timeline-based JSON events for live sync and audit tracing:
- Detected anomalies and live error streams
- AI-generated suggestions
- Specific validation results (approved/rejected fixes)
- Executed commands and final remediation outcomes

---

## 🚀 Getting Started

*(Local configuration and deployment instructions to be added as development progresses.)*
