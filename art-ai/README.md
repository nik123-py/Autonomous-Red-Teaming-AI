<p align="center">
  <h1 align="center">🛡️ ART-AI: Autonomous Red Team AI</h1>
  <p align="center">
    <strong>Continuous, intelligent red teaming powered by Knowledge-Augmented Reinforcement Learning</strong>
  </p>
  <p align="center">
    <em>One platform: Network Scanner · Vulnerability Scanner · Exploit Generator · Code Analysis · AI Assistant · Autonomous Scheduler</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/react-18+-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/fastapi-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-educational-orange" alt="License">
</p>

---

## 🚀 What is ART-AI?

ART-AI is a **full-stack autonomous red teaming platform** that uses **Knowledge-Augmented Reinforcement Learning (KARL)** to simulate offensive security operations. Unlike traditional tools that rely on fixed playbooks, ART-AI's Q-learning agent **learns from attack outcomes** and is guided by **Exploit-DB intelligence** to prioritize known vulnerability vectors — all within a safe, sandboxed environment.

> **Not a concept — a fully working MVP with 12+ dashboard pages, 20+ API endpoints, and a complete pentester toolkit.**

---

## 🏆 Competitive Edge

| Feature | ART-AI | FireCompass | Cymulate | Pentera | Synack |
|---------|--------|-------------|----------|---------|--------|
| Knowledge-Augmented RL | ✅ | ❌ Fixed playbooks | ❌ Predefined threats | ❌ | ❌ |
| Autonomous Scheduler | ✅ 10–20 min cadence | ❌ | Partial | ❌ | ❌ |
| In-Tool AI Assistant | ✅ Chat + Exploit ideas | ❌ | ❌ | ❌ | ❌ |
| Full Pentester Toolkit | ✅ 7+ tools in one UI | Partial | Partial | Partial | ❌ Crowd-sourced |
| Code Vulnerability Analysis | ✅ C/C++ + ML model | ❌ | ❌ | ❌ | ❌ |
| Compliance Dashboard | ✅ Evidence & reports | ❌ | Partial | Partial | ❌ |

**One-line differentiator:** ART-AI is the only platform combining RL + Exploit-DB intel + autonomous scheduling + AI assistant + a full pentester toolkit — built to **multiply analyst output**, not replace them.

---

## ✨ Features

### 🔧 Core Pentester Toolkit
| Tool | Description |
|------|-------------|
| **🌐 Network Scanner** | Port scanning, service discovery, OS fingerprinting |
| **🔍 Vulnerability Scanner** | Multi-engine vuln detection with ML-powered predictions |
| **💥 Exploit Generator** | Auto-generates 10+ exploit types (SQLi, XSS, RCE, SSRF, XXE, etc.) |
| **📝 Code Analysis** | C/C++ source code vulnerability detection using ML models |
| **📊 Attack History** | Stored attack paths with interactive graph visualization |
| **📋 Compliance Dashboard** | Security posture scoring, evidence collection for auditors |
| **📄 Report Generation** | Automated penetration test report creation |

### 🤖 AI & Automation
| Feature | Description |
|---------|-------------|
| **🧠 RL Agent (Q-Learning)** | Learns optimal attack paths through exploration and exploitation |
| **📚 Exploit-DB Integration** | Strategic hints from CVE/exploit databases guide the agent |
| **⏱️ Autonomous Scheduler** | Continuous red teaming every 10–20 minutes without re-trigger |
| **💬 Pentest AI Assistant** | In-tool chat (Ollama/Gemini) for next-step guidance and exploit ideas |
| **🛡️ Quantum Defender** | Advanced threat simulation and defense analysis |

### 🎯 Attack Capabilities
- **10+ Attack Types:** Public access, auth bypass, SQL injection, XSS, token reuse, session hijack, path traversal, command injection, privilege escalation, lateral movement
- **10 Exploit Types Generated:** SQL injection (UNION/Boolean/Time-based), XSS (Reflected/Stored/DOM), Command injection, Path traversal, Auth bypass, Privilege escalation, SSRF, XXE, Deserialization, Template injection
- **4 Access Levels Tracked:** None → Public → Internal → Admin (with escalation logic)
- **Knowledge-Augmented Rewards:** +100 massive reward for following Exploit-DB hints successfully, +2 for matching hints, -1 for ignoring hints

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     👤 Penetration Tester                        │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                  Frontend (React + Vite)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Network  │ │  Vuln    │ │ Exploit  │ │  Code Analysis   │   │
│  │ Scanner  │ │ Scanner  │ │Generator │ │  (C/C++ + ML)    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │Autonomous│ │ Pentest  │ │ Attack   │ │  Compliance &    │   │
│  │Scheduler │ │AI  Chat  │ │ History  │ │  Report Gen      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────┬───────────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼───────────────────────────────────────────┐
│                   Backend (FastAPI)                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Q-Learning  │  │  Exploit-DB  │  │    Attack Engine       │  │
│  │  RL Agent   │──│  Knowledge   │  │  (Simulation Engine)   │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Recon     │  │   Exploit    │  │  ML Vulnerability      │  │
│  │   Engine    │  │  Generator   │  │  Detection Model       │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  SQLite     │  │  Chat API    │  │  Compliance &          │  │
│  │  Storage    │  │(Ollama/Gemini│  │  Report Generator      │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│              Target Environments                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐              │
│  │  Juice   │  │   DVWA   │  │  Custom Vuln API │              │
│  │  Shop    │  │          │  │                  │              │
│  └──────────┘  └──────────┘  └──────────────────┘              │
│              Docker Lab (Safe & Sandboxed)                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
art-ai/
├── backend/
│   ├── main.py                    # FastAPI app (20+ endpoints)
│   ├── ai_agent.py                # Q-learning RL agent
│   ├── ai_agent_optimized.py      # Optimized RL agent variant
│   ├── attack_engine.py           # Attack simulation engine
│   ├── env.py                     # Environment state model
│   ├── storage.py                 # Attack path storage (SQLite)
│   ├── recon.py                   # Network/port scanning
│   ├── vulnerability_scanner.py   # Multi-engine vuln scanner
│   ├── exploit_generator.py       # Custom exploit generation
│   ├── ml_vulnerability_model.py  # ML-based vuln detection
│   ├── exploit_ml_models.py       # ML models for exploit analysis
│   ├── exploit_vector_store.py    # Exploit vector embeddings
│   ├── exploit_data_processor.py  # Exploit data processing
│   ├── decision_maker.py          # AI decision engine
│   ├── compliance.py              # Compliance scoring engine
│   ├── report_generator.py        # Automated report generation
│   ├── vul_model.py               # Vulnerability model definitions
│   ├── ai/
│   │   └── knowledge.py           # Exploit-DB librarian
│   ├── models/                    # Pre-trained ML models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main app with routing
│   │   ├── pages/
│   │   │   ├── HomePage.jsx              # Dashboard home
│   │   │   ├── SimulationPage.jsx        # RL attack simulation
│   │   │   ├── NetworkScanPage.jsx       # Network reconnaissance
│   │   │   ├── VulnScanPage.jsx          # Vulnerability scanning
│   │   │   ├── ExploitGeneratorPage.jsx  # Exploit crafting
│   │   │   ├── CodeAnalysisPage.jsx      # C/C++ code analysis
│   │   │   ├── AttackHistoryPage.jsx     # Historical attack paths
│   │   │   ├── AutonomousSchedulerPage.jsx # Auto scheduler
│   │   │   ├── PentestChatPage.jsx       # AI pentest assistant
│   │   │   ├── RLAgentPage.jsx           # RL agent dashboard
│   │   │   ├── ComplianceDashboardPage.jsx # Compliance overview
│   │   │   ├── ReportGenerationPage.jsx  # Report builder
│   │   │   └── QuantumDefenderPage.jsx   # Threat simulation
│   │   └── components/            # Reusable UI components
│   ├── package.json
│   └── vite.config.js
├── lab/
│   ├── docker-compose.yml         # Vulnerable lab setup
│   └── vulnerable-api/            # Custom vulnerable API
├── start.bat                      # Windows quick start
├── start.sh                       # Linux/Mac quick start
└── run-project.bat                # Alternative Windows launcher
```

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Docker & Docker Compose** (for vulnerable lab)

### Option 1: One-Click Start (Windows)
```bash
# From the art-ai directory
start.bat
```

### Option 2: Manual Setup

#### 1. Start the Vulnerable Lab
```bash
cd lab
docker-compose up -d
```
This launches:
- 🧃 **Juice Shop** → http://localhost:3001
- 🛡️ **DVWA** → http://localhost:3002
- 🔌 **Vulnerable API** → http://localhost:3003

#### 2. Start the Backend
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python main.py
```
- 🖥️ Backend API → http://localhost:8003
- 📖 Swagger Docs → http://localhost:8003/docs

#### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
- 🌐 Dashboard → http://localhost:3000

---

## 🎮 Usage Guide

### 🤖 Running an AI Attack Simulation
1. Navigate to **Simulation** page
2. Set iterations (50–100 recommended for demo)
3. Optionally specify a target host
4. Click **"Start Simulation"**
5. Watch the RL agent explore attack paths in real-time
6. View the interactive attack path graph — successful paths (green), failed (gray), blocked (red)

### 🌐 Network & Vulnerability Scanning
1. Go to **Network Scanner** or **Vulnerability Scanner**
2. Enter target IP/hostname
3. Choose scan type (Full / Port-only / Vuln-only)
4. Review discovered ports, services, and vulnerabilities
5. Auto-generated exploits appear for each vulnerability found

### 💥 Exploit Generation
1. Open **Exploit Generator**
2. Select exploit type (SQLi, XSS, RCE, etc.)
3. Configure target endpoint and parameters
4. Generate custom payloads with success probability scores

### 📝 Code Vulnerability Analysis
1. Open **Code Analysis**
2. Paste or upload C/C++ source code
3. ML model analyzes for buffer overflows, injection flaws, etc.
4. Get severity ratings and remediation suggestions

### ⏱️ Autonomous Scheduling
1. Go to **Autonomous Scheduler**
2. Set target and interval (10–20 minutes)
3. Enable autonomous mode
4. System runs continuous scan → exploit → attack cycles without manual re-trigger

### 💬 Pentest AI Assistant
1. Open **Pentest Chat**
2. Ask questions like: *"What should I try after finding an open SSH port?"*
3. Get contextual guidance, exploit suggestions, and next-step recommendations

---

## 🧠 How Knowledge-Augmented RL Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Scan Target │────▶│  Discover Apache │────▶│ Query Exploit-DB│
│  (Recon)     │     │  2.4.49 service  │     │ for known CVEs  │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │ Strategic Hint:  │
                                              │ PATH_TRAVERSAL   │
                                              │ (CVE-2021-41773) │
                                              └────────┬────────┘
                                                       │
┌─────────────┐     ┌──────────────────┐     ┌────────▼────────┐
│  Agent gets  │◀────│  +100 Reward if  │◀────│ Agent prioritizes│
│  smarter over│     │  hint succeeds!  │     │ path traversal   │
│  iterations  │     │  +2 for matching │     │ attacks (80%)    │
└─────────────┘     └──────────────────┘     └─────────────────┘
```

**Reward Structure:**
| Event | Reward |
|-------|--------|
| Access level escalation | +10 |
| Successful attack | +5 |
| Vulnerability discovered | +3 |
| Action matches Exploit-DB hint | +2 bonus |
| Following hint leads to success | **+100** |
| Failed attempt | -2 |
| Ignoring available hint & failing | -1 |
| Blocked by defenses | -10 |

---

## 🔌 API Reference

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **State** | `/api/state` | GET | Current environment state |
| **State** | `/api/reset` | POST | Reset environment |
| **Attack** | `/api/attack` | POST | Execute single attack |
| **Attack** | `/api/simulate` | POST | Run full AI simulation |
| **Attack** | `/api/available-actions` | GET | List available actions |
| **Scanning** | `/api/scan` | POST | Network + vuln scan |
| **Scanning** | `/api/analyze-system` | POST | System weakness analysis |
| **Exploits** | `/api/generate-exploit` | POST | Generate custom exploit |
| **Exploits** | `/api/generated-exploits` | GET | List all generated exploits |
| **Analysis** | `/api/analyze-code` | POST | Analyze code for vulnerabilities |
| **History** | `/api/attack-paths` | GET | All stored attack paths |
| **History** | `/api/best-path` | GET | Best attack path found |
| **AI Chat** | `/api/chat` | POST | Pentest AI assistant |

Full interactive API documentation available at http://localhost:8003/docs

---

## 🛡️ Security Disclaimer

> **⚠️ IMPORTANT:** ART-AI is designed for **educational and authorized testing purposes only**. All attacks are simulated within sandboxed environments. The vulnerable lab Docker containers are intentionally insecure and must **never** be exposed to the internet. Always obtain proper authorization before testing any system.

---

## 🔧 Development

### Adding New Attack Actions
1. Add to `AttackAction` enum in `attack_engine.py`
2. Define success probabilities in `SUCCESS_PROBABILITIES`
3. Add access escalation mapping in `ACCESS_ESCALATIONS`

### Tuning the RL Agent
- **Learning rate**: `0.1` (default) — adjust in `ai_agent.py`
- **Discount factor**: `0.9` (default)
- **Hint prioritization**: `80%` probability of following Exploit-DB hint

### Swapping AI Provider
The Pentest Chat supports multiple backends:
- **Ollama** (local, free)
- **Google Gemini** (cloud API)
- Configure in `.env` file

---

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, ReactFlow, Recharts, Axios |
| Backend | Python 3.11, FastAPI, Uvicorn |
| AI/ML | Q-Learning, PyTorch, NumPy |
| Database | SQLite |
| Lab | Docker, OWASP Juice Shop, DVWA |
| AI Chat | Ollama / Google Gemini API |

---

## 📜 License

Educational use only. See LICENSE file for details.

---

<p align="center">
  <strong>Built with 🔥 for the THREX Hackathon</strong><br>
  <em>ART-AI — Autonomous. Intelligent. Continuous.</em>
</p>
