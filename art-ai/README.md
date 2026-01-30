# ART-AI: Autonomous Red Team AI MVP

A sandboxed offensive security simulation system that uses reinforcement learning to explore vulnerable environments and generate attack paths.

## Overview

ART-AI is a fully functional MVP that simulates autonomous red team operations using reinforcement learning. The system explores vulnerable environments, learns from attack outcomes, and generates optimal attack paths - all in a safe, sandboxed environment.

## Architecture

- **Backend**: FastAPI with Q-learning RL agent
- **Frontend**: React dashboard with interactive attack path visualization
- **Lab**: Docker-based vulnerable environments (Juice Shop, DVWA, Custom API)

## Features

- **Abstract Attack Simulation**: 10+ attack action types (SQL injection, XSS, privilege escalation, etc.)
- **Knowledge-Augmented Reinforcement Learning**: Q-learning agent enhanced with Exploit-DB strategic hints
- **Exploit-DB Integration**: Queries Exploit-DB (via searchsploit or mock database) for attack vector suggestions
- **Strategic Hint System**: AI receives hints from Exploit-DB and learns to prioritize known vulnerabilities
- **Network & Port Scanning**: Simulated reconnaissance with service discovery
- **Vulnerability Scanning**: Multi-tool vulnerability detection system
- **Dynamic Exploit Generation**: Creates custom exploits based on discovered vulnerabilities and system analysis
- **System Weakness Analysis**: Identifies system weaknesses and crafts targeted exploits
- **Attack Path Visualization**: Interactive graph showing successful/failed attack sequences
- **Attack Path Storage**: SQLite database for tracking and analyzing attack paths
- **Sandboxed Environment**: No real exploits - safe for demonstration

## Project Structure

```
art-ai/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── attack_engine.py        # Attack simulation engine
│   ├── ai_agent.py            # Q-learning RL agent
│   ├── env.py                 # Environment state model
│   ├── storage.py             # Attack path storage (SQLite)
│   ├── recon.py               # Network/port scanning
│   ├── vulnerability_scanner.py  # Vulnerability scanning tools
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main application
│   │   ├── components/
│   │   │   ├── Dashboard.jsx  # Control panel
│   │   │   ├── AttackPathVisualization.jsx  # Graph visualization
│   │   │   └── ScanPanel.jsx  # Network/vuln scanner UI
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── lab/
│   ├── docker-compose.yml     # Vulnerable lab setup
│   └── vulnerable-api/        # Custom vulnerable API
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

## Installation & Setup

### 1. Clone and Navigate
```bash
cd art-ai
```

### 2. Start Vulnerable Lab
```bash
cd lab
docker-compose up -d
```

This starts:
- **Juice Shop** on http://localhost:3001
- **DVWA** on http://localhost:3002
- **Vulnerable API** on http://localhost:3003

### 3. Setup Backend
```bash
cd ../backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Start Backend Server
```bash
python main.py
```

Backend runs on http://localhost:8000
API docs available at http://localhost:8000/docs

### 5. Setup Frontend
```bash
cd ../frontend
npm install
```

### 6. Start Frontend
```bash
npm run dev
```

Frontend runs on http://localhost:3000

## Usage

### Running a Simulation

1. **Open Dashboard**: Navigate to http://localhost:3000
2. **Configure Simulation**:
   - Set iterations (default: 100)
   - Optionally specify target host for reconnaissance
3. **Start Simulation**: Click "Start Simulation"
4. **View Results**:
   - Watch attack path graph build in real-time
   - See successful/failed attacks
   - Check final access level achieved
   - Review discovered vulnerabilities

### Network & Vulnerability Scanning

1. **Open Scan Panel**: Located in the sidebar
2. **Enter Target**: IP address or hostname
3. **Select Scan Type**:
   - **Full Scan**: Ports + Vulnerabilities + Exploit Generation
   - **Port Scan Only**: Network reconnaissance
   - **Vulnerability Scan Only**: Security assessment
4. **Start Scan**: Click "Start Scan"
5. **Review Results**: View open ports, services, vulnerabilities, and **generated exploits**

### Exploit Generation

The system automatically generates custom exploits when vulnerabilities are discovered:

1. **System Analysis**: Analyzes discovered services and vulnerabilities
2. **Weakness Identification**: Identifies specific system weaknesses
3. **Exploit Crafting**: Creates targeted payloads based on:
   - Vulnerability type
   - Affected services
   - System configuration
   - Success probability calculations
4. **Exploit Details**: Each exploit includes:
   - Custom payload
   - Target endpoint and parameters
   - Success probability
   - Impact assessment
   - System weakness analysis
   - Vulnerability analysis
   - Remediation recommendations

**Exploit Types Generated:**
- SQL Injection (UNION, Boolean-based, Time-based)
- Cross-Site Scripting (Reflected, Stored, DOM-based)
- Command Injection (OS commands, Code execution)
- Path Traversal (Directory traversal, Zip Slip)
- Authentication Bypass (SQL injection, Session manipulation)
- Privilege Escalation (IDOR, Parameter tampering)
- SSRF (Server-Side Request Forgery)
- XXE (XML External Entity)
- Deserialization attacks
- Template Injection

### API Endpoints

**State Management**
- `GET /api/state` - Get current environment state
- `POST /api/reset` - Reset environment

**Attack Execution**
- `POST /api/attack` - Execute single attack action
- `POST /api/simulate` - Run full AI simulation
- `GET /api/available-actions` - Get available actions

**Scanning**
- `POST /api/scan` - Network/vulnerability scan (includes exploit generation)
- `POST /api/analyze-system` - Analyze system weaknesses

**Exploit Generation**
- `POST /api/generate-exploit` - Generate custom exploit for vulnerability type
- `GET /api/generated-exploits` - Get all generated exploits

**Attack Paths**
- `GET /api/attack-paths` - Get all stored paths
- `GET /api/best-path` - Get best attack path

## Attack Actions

The system supports 10+ abstract attack actions:

- `public_access_attempt` - Initial access attempts
- `authentication_bypass_attempt` - Bypass authentication
- `sql_injection_attempt` - SQL injection attacks
- `xss_attempt` - Cross-site scripting
- `token_reuse_attempt` - Token/session reuse
- `session_hijack_attempt` - Session hijacking
- `path_traversal_attempt` - Directory traversal
- `command_injection_attempt` - Command injection
- `privilege_escalation_attempt` - Escalate privileges
- `lateral_movement_attempt` - Move between systems

## Access Levels

The system tracks 4 access levels:

1. **NONE** - No access
2. **PUBLIC** - Public/unauthenticated access
3. **INTERNAL** - Authenticated internal access
4. **ADMIN** - Administrative access

## Knowledge-Augmented Reinforcement Learning

The Q-learning agent is enhanced with Exploit-DB strategic hints:

### Strategic Hint System
- **Exploit-DB Integration**: Queries Exploit-DB (via `searchsploit` or mock database) for known vulnerabilities
- **Service-Based Hints**: Analyzes discovered services and suggests attack vectors
- **Demo Mode**: Includes hardcoded hints for common services (Apache, MySQL, PostgreSQL, etc.)
- **Real Mode**: Uses `searchsploit` if installed for live Exploit-DB queries

### Reward Structure
- **Base Rewards**:
  - +10 for access escalation
  - +5 for successful attack
  - +3 for vulnerability discovery
  - -2 for failed attempt
  - -10 if blocked
- **Knowledge-Augmented Rewards**:
  - **+2 bonus** if action matches strategic hint (trusting intel)
  - **+100 massive reward** if following hint succeeds (validating intel)
  - **-1 penalty** for ignoring available hint and failing

### Learning Behavior
- Agent starts by exploring randomly
- When Exploit-DB provides a hint, agent learns to prioritize that attack vector
- High rewards for following hints teach the agent to trust known vulnerability intelligence
- Agent quickly adapts to exploit known CVEs and vulnerabilities

### Example Flow
1. Scan discovers "Apache 2.4.49"
2. Exploit-DB Librarian suggests: `PATH_TRAVERSAL` (CVE-2021-41773)
3. Agent receives hint and prioritizes path traversal attacks
4. If successful, agent receives +100 reward and learns to trust Exploit-DB hints
5. Future encounters with Apache 2.4.49 trigger immediate path traversal attempts

## Demo Flow

1. Start vulnerable lab (Docker)
2. Start backend API (`python main.py`)
3. Start frontend (`npm run dev`)
4. Open http://localhost:3000
5. Click "Start Simulation"
6. AI runs 50-100 iterations
7. Attack path graph appears showing:
   - Failed attempts (gray)
   - Successful attacks (colored by access level)
   - Blocked attacks (red)
   - Final breach path (green)
8. Review statistics and discovered vulnerabilities

## Security Note

**IMPORTANT**: This system is designed for educational and demonstration purposes only. All attacks are simulated and do not execute real exploits. The vulnerable lab environments are intentionally insecure and should never be exposed to the internet.

## Troubleshooting

**Backend won't start**
- Check Python version (3.11+)
- Verify all dependencies installed
- Check port 8000 is available

**Frontend won't start**
- Check Node.js version (18+)
- Run `npm install` again
- Check port 3000 is available

**Docker containers won't start**
- Ensure Docker is running
- Check ports 3001-3003 are available
- Try `docker-compose down` then `docker-compose up -d`

**API connection errors**
- Verify backend is running on port 8000
- Check CORS settings in `main.py`
- Check browser console for errors

## Development

### Adding New Attack Actions

1. Add action to `AttackAction` enum in `attack_engine.py`
2. Define success probabilities in `SUCCESS_PROBABILITIES`
3. Add access escalation mapping in `ACCESS_ESCALATIONS`

### Customizing RL Agent

Edit `ai_agent.py`:
- Adjust `learning_rate` (default: 0.1)
- Adjust `discount_factor` (default: 0.9)
- Modify reward calculation in `calculate_reward()` (includes hint-based rewards)
- Adjust hint prioritization probability in `choose_action()` (default: 80%)

### Customizing Exploit-DB Integration

Edit `ai/knowledge.py`:
- Add more services to `_load_mock_exploit_db()` for demo mode
- Adjust hint confidence levels
- Modify `_infer_action_from_title()` to improve exploit-to-action mapping
- Set `demo_mode=False` in `main.py` to use real `searchsploit` (if installed)

### Adding Vulnerability Checks

Edit `vulnerability_scanner.py`:
- Add vulnerabilities to `SERVICE_VULNERABILITIES`
- Implement custom scan logic in `scan_target()`

### Customizing Exploit Generation

Edit `exploit_generator.py`:
- Add exploit templates to `_load_exploit_templates()`
- Customize payload crafting in `_craft_payload()`
- Adjust success probability calculations in `_calculate_success_probability()`
- Enhance system analysis in `analyze_system()`

## License

Educational use only. See LICENSE file for details.

## Contributing

This is an MVP for demonstration purposes. Contributions welcome for:
- Additional attack actions
- Improved RL algorithms
- Enhanced visualization
- More vulnerability checks

## Support

For issues or questions, please check:
- Backend logs: Console output from `python main.py`
- Frontend logs: Browser developer console
- Docker logs: `docker-compose logs`

