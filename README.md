<p align="center">
  <img src="https://img.shields.io/badge/HackByte_4.0-2026-blueviolet?style=for-the-badge" alt="HackByte 4.0" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Solidity-^0.8.20-363636?style=for-the-badge&logo=solidity&logoColor=white" alt="Solidity" />
</p>

<h1 align="center">🌌 XOne — Patch the Reality</h1>

<p align="center">
  <strong>Detect, Diagnose, and Deploy Fixes — Before the Pager Even Rings.</strong>
</p>

<p align="center">
  <em>An autonomous, AI-driven infrastructure remediation platform with blockchain-verified audit trails and real-time policy enforcement.</em>
</p>

---

## 🎯 The Problem

Modern infrastructure teams are trapped in a reactive cycle: an alert fires at 3 AM, an engineer wakes up, spends 40 minutes diagnosing the issue, applies a fix, and prays it holds. **XOne eliminates this loop entirely.**

## 💡 The Solution

XOne is an **autonomous system recovery platform** that:
1. **SSHs into your production server** and collects system telemetry (PM2 logs, systemd journals, disk/memory/CPU snapshots)
2. **Diagnoses the root cause** using Google Gemini with structured reasoning
3. **Generates a multi-step remediation plan** with risk assessments
4. **Enforces safety policies** — blocking destructive actions like `DROP TABLE` or `rm -rf /` before they ever execute
5. **Executes approved fixes** autonomously on the target server
6. **Verifies the resolution** and retries if the incident persists (up to 3 passes)
7. **Logs everything immutably** to a Solidity smart contract on-chain for tamper-proof audit trails

> **Core Principle:** XOne **never blindly trusts AI**. Every AI-proposed action passes through a policy enforcement layer before touching your infrastructure.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                        │
│  Dashboard │ Command Center │ Terminal │ SQL Monitor │ Blockchain Verify│
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ SSE Stream + REST API
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Django 6 + DRF + SimpleJWT)                 │
│         Auth (Google/GitHub OAuth)  │  Project CRUD  │  Agent Runner    │
└──────────────────┬────────────────────────────┬──────────────────────────┘
                   │                            │
                   ▼                            ▼
┌──────────────────────────┐   ┌────────────────────────────────────────┐
│   PostgreSQL (Persistent)│   │       AI ENGINE (LangGraph Pipeline)   │
│   Users, Projects, Keys  │   │                                        │
└──────────────────────────┘   │  collect → diagnose → plan → enforce   │
                               │             → execute → verify → loop  │
┌──────────────────────────┐   └──────┬─────────────────┬───────────────┘
│  SpacetimeDB (Real-Time) │          │                 │
│  Incidents, Events, AI   │◄─────────┘                 │ SSH
│  Decisions, Safety Logs  │                            ▼
└──────────────────────────┘              ┌──────────────────────┐
                                          │  TARGET SERVER (VPS) │
┌──────────────────────────┐              │  PM2, Nginx, Node.js │
│  Blockchain (Hardhat/EVM)│              └──────────────────────┘
│  XOneAuditPatch.sol      │
│  Immutable Patch Records │
└──────────────────────────┘
```

---

## 🧠 The AI Agent Pipeline

The heart of XOne is a **6-node LangGraph state machine** that orchestrates the full incident lifecycle:

| Node | Responsibility |
|------|---------------|
| **`collect`** | SSHs into the target server. Pulls PM2 logs, systemd journals, system snapshots (CPU, memory, disk), Nginx/Redis configs, and custom deploy logs. |
| **`diagnose`** | Sends collected telemetry to Google Gemini. Returns structured JSON with `error_type`, `root_cause`, `severity`, `confidence`, and proposed `actions[]`. |
| **`plan`** | Converts diagnosis actions into a sequenced **Intent Plan** — each step tagged with `risk_level`, `reversible` flag, and execution priority. |
| **`enforce`** | Runs every intent through the **ArmorIQ Policy Engine**. Destructive/irreversible actions (e.g., `DROP TABLE`, `rm -rf`) are **blocked** with a policy ID and reason. Safe actions are **allowed**. |
| **`execute`** | Executes only ALLOWED intents on the target server via SSH. Captures stdout/stderr for each action. Records success/failure status. |
| **`verify`** | Re-collects fresh logs post-fix. If the incident persists, loops back to `collect` (max 3 retries). If resolved, marks the incident as closed. |

```
┌─────────┐    ┌──────────┐    ┌──────┐    ┌─────────┐    ┌─────────┐    ┌────────┐
│ COLLECT │───▶│ DIAGNOSE │───▶│ PLAN │───▶│ ENFORCE │───▶│ EXECUTE │───▶│ VERIFY │
└─────────┘    └──────────┘    └──────┘    └─────────┘    └─────────┘    └───┬────┘
     ▲                                                                       │
     │                              if NOT resolved (max 3 retries)          │
     └───────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Policy Enforcement (ArmorIQ)

Not all AI suggestions are safe. XOne's enforce node applies **hard policy rules**:

| Policy | Rule | Example Blocked Action |
|--------|------|----------------------|
| `P-001` | Block destructive irreversible operations | `DROP TABLE`, `rm -rf /` |
| `P-002` | Block privilege escalation | `chmod 777`, `sudo su` |
| `P-003` | Block network exposure changes | `ufw disable`, `iptables -F` |
| `local-fallback` | When ArmorIQ API is unreachable, apply conservative local rules | Low-risk actions allowed, anything `medium+` blocked |

**Every enforcement decision is logged** to SpacetimeDB in real-time and visible in the Command Center terminal.

---

## ⛓️ Blockchain Audit Trail

When an incident is resolved, the full remediation record is logged **immutably** on-chain:

```solidity
// contracts/XOneAuditPatch.sol
contract XOneAuditPatch {
    struct PatchRecord {
        string projectId;
        string cid;          // IPFS Content ID of the full audit payload
        uint256 timestamp;
    }

    function logPatch(string memory _projectId, string memory _cid) public { ... }
    function getPatch(uint256 index) public view returns (...) { ... }
}
```

The frontend's **"Verify Integrity"** modal lets users input a Transaction Hash and instantly verify:
- What was patched
- When it was patched  
- What the AI decided
- What was blocked by policy
- Whether the data has been tampered with

---

## 📁 Project Structure

```
hackbyte4/
├── frontend/                    # React 18 + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/
│   │   │   ├── Terminal.jsx           # Live agent output terminal
│   │   │   ├── SQLMonitor.jsx         # Real-time SpacetimeDB event viewer
│   │   │   ├── BlockchainVerifyModal  # On-chain verification UI
│   │   │   ├── AddProjectModal.jsx    # Project creation form
│   │   │   └── home.jsx              # Landing page
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx          # Project overview + dynamic greeting
│   │   │   ├── CommandCenter.jsx      # Agent control + live terminal
│   │   │   ├── Auth.jsx               # Google/GitHub OAuth login
│   │   │   └── ProjectData.jsx        # Project details + config editing
│   │   ├── hooks/
│   │   │   └── useSpacetimeDB.js      # Real-time SpacetimeDB subscription
│   │   └── lib/
│   │       ├── api.js                 # REST + SSE client functions
│   │       └── logToBlockchain.js     # Ethers.js blockchain logging
│   └── Dockerfile
│
├── backend/
│   ├── core/                    # Django 6.0 Project
│   │   ├── core/                      # Django settings, urls, wsgi/asgi
│   │   ├── authenticationApp/         # CustomUser model + social OAuth
│   │   └── UserProjects/             # Project model, ViewSet, agent runner
│   ├── ai_engine/               # LangGraph AI Pipeline
│   │   ├── graph.py                   # State machine definition + SSE stream
│   │   ├── nodes/
│   │   │   ├── collect.py             # SSH log collection
│   │   │   ├── diagnose.py            # Gemini-powered root cause analysis
│   │   │   ├── plan.py                # Intent plan generation
│   │   │   ├── enforce.py             # ArmorIQ policy enforcement
│   │   │   ├── execute.py             # SSH command execution
│   │   │   └── verify.py              # Post-fix verification loop
│   │   ├── tools/                     # VMTools (SSH), SpacetimeTools, GeminiTools
│   │   └── policies/                  # Policy rule definitions
│   ├── pyproject.toml           # UV dependency lock
│   ├── uv.lock                  # Reproducible dependency resolution
│   └── Dockerfile
│
├── blockchain/                  # Hardhat + Solidity
│   ├── contracts/
│   │   └── XOneAuditPatch.sol         # Immutable audit log smart contract
│   ├── scripts/                       # Deploy + interaction scripts
│   ├── hardhat.config.ts
│   └── Dockerfile
│
├── realitypatch-db/             # SpacetimeDB Module
│   └── spacetimedb/                   # Rust module (tables, reducers)
│
├── docker-compose.yml           # One-command full stack orchestration
└── .dockerignore
```

---

## 🚀 Getting Started

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- **Node.js** ≥ 20 and **npm**
- **Python** ≥ 3.13 and **[uv](https://docs.astral.sh/uv/)**
- **SpacetimeDB CLI** — [Install Guide](https://spacetimedb.com/install)

### Option 1: Docker (Recommended)

The entire stack launches with a single command:

```bash
# Clone the repository
git clone https://github.com/your-org/xone.git
cd xone

# Create your environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your GEMINI_API_KEY, SECRET_KEY, OAuth credentials

# Launch everything
docker-compose up --build
```

This starts **5 services** simultaneously:

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | [localhost:5173](http://localhost:5173) | Vite React dev server |
| `backend` | [localhost:8000](http://localhost:8000) | Django REST API |
| `db` | `5432` | PostgreSQL 15 |
| `hardhat` | `8545` | Local EVM blockchain |
| `spacetimedb` | `3000` | Real-time event database |

### Option 2: Manual Setup

<details>
<summary><strong>Click to expand manual setup instructions</strong></summary>

#### Backend

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies with UV
uv sync

# Run migrations
cd core
python manage.py migrate
python manage.py runserver localhost:8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Blockchain (Local Hardhat Node)

```bash
cd blockchain
npm install
npx hardhat node
```

#### SpacetimeDB

```bash
cd realitypatch-db
spacetime start
spacetime publish realitypatch-db-2lsay
```

</details>

---

## ⚙️ Environment Variables

Create `backend/.env` with:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# AI Engine
GEMINI_API_KEY=your-google-gemini-api-key

# Database (Docker uses these automatically)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=dhurandar
DB_USER=root
DB_PASSWORD=your-db-password
DB_HOST=db
DB_PORT=5432
```

---

## 💾 Data Architecture

### PostgreSQL — Persistent Business Logic
| Table | Purpose |
|-------|---------|
| `CustomUser` | Extended Django user with `google_id`, `github_id`, social auth fields |
| `Project` | Server configurations: IP, SSH key, root directory, deploy commands |

### SpacetimeDB — Real-Time Operational Telemetry
| Table | Purpose |
|-------|---------|
| `Project` | Mirrored project metadata for real-time subscriptions |
| `Incident` | Live incident tracking with status lifecycle |
| `AgentEvent` | Every pipeline event (node starts, completions, errors) |
| `AiDecision` | Structured diagnosis output from Gemini |
| `SafetyCheck` | Policy enforcement decisions (ALLOWED / BLOCKED) |
| `Execution` | SSH command execution results and outputs |

### Blockchain — Immutable Audit Records
| Contract | Purpose |
|----------|---------|
| `XOneAuditPatch` | Stores `(projectId, IPFS CID, timestamp)` for every resolved incident |

---

## 🛠️ Tech Stack

<table>
<tr><td><strong>Layer</strong></td><td><strong>Technology</strong></td></tr>
<tr><td>Frontend</td><td>React 18, Vite, TailwindCSS, Lucide Icons, Three.js, Ethers.js</td></tr>
<tr><td>Backend</td><td>Django 6.0, Django REST Framework, SimpleJWT, dj-rest-auth, django-allauth</td></tr>
<tr><td>AI Engine</td><td>LangGraph, LangChain Core, Google Gemini (generative AI)</td></tr>
<tr><td>Real-Time DB</td><td>SpacetimeDB (Rust module + JS SDK)</td></tr>
<tr><td>Relational DB</td><td>PostgreSQL 15</td></tr>
<tr><td>Blockchain</td><td>Solidity ^0.8.20, Hardhat, Ethers.js v6</td></tr>
<tr><td>SSH</td><td>Paramiko (Python SSH2 client)</td></tr>
<tr><td>Package Manager</td><td>UV (Python), npm (Node.js)</td></tr>
<tr><td>Containerization</td><td>Docker, Docker Compose</td></tr>
</table>

---

## 📸 Screenshots

> *Add screenshots of your Dashboard, Command Center terminal, Blockchain Verify modal, and Landing Page here.*

---

## 👥 Team

Built with ❤️ at **HackByte 4.0**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
