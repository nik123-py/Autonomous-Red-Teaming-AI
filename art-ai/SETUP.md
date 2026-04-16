# 🛡️ ART-AI — Complete Project Setup Guide

> **Autonomous Red Teaming AI** — Step-by-step instructions to set up and run the entire project from scratch on a fresh Windows machine.

---

## Table of Contents

1. [Prerequisites (Downloads)](#1-prerequisites-downloads)
2. [Clone the Repository](#2-clone-the-repository)
3. [Backend Setup](#3-backend-setup)
4. [Frontend Setup](#4-frontend-setup)
5. [Vulnerable Lab Setup (Docker)](#5-vulnerable-lab-setup-docker)
6. [Kali Linux Setup (Docker)](#6-kali-linux-setup-docker)
7. [Running the Project](#7-running-the-project)
8. [Port Reference & URLs](#8-port-reference--urls)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites (Downloads)

You need to install the following software **before** setting up the project. Download and install each one:

| Software | Version | Download Link | Why It's Needed |
|----------|---------|---------------|-----------------|
| **Git** | Latest | [git-scm.com/downloads](https://git-scm.com/downloads) | Clone the repository |
| **Python** | 3.9 or higher | [python.org/downloads](https://www.python.org/downloads/) | Backend server (FastAPI) |
| **Node.js** | LTS (v18+) | [nodejs.org](https://nodejs.org/) | Frontend dev server (Vite + React) |
| **Docker Desktop** | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | Kali Linux & Vulnerable Labs |

### ⚠️ Important Installation Notes

- **Python**: During installation, **check the box** that says _"Add python.exe to PATH"_ at the bottom of the installer. Without this, commands like `python` and `pip` will not work.
- **Node.js**: The installer automatically adds `node` and `npm` to PATH — no extra steps needed.
- **Docker Desktop**: Requires Windows 10/11 with **virtualization enabled** in BIOS/UEFI. Docker Desktop will prompt you to enable WSL 2 if it's not already set up — follow the on-screen instructions.

### Verify Installations

After installing everything, open **Command Prompt** or **PowerShell** and run these commands to verify:

```cmd
git --version
python --version
node --version
npm --version
docker --version
```

All commands should return version numbers without errors. If any command fails, revisit the installation step for that tool.

---

## 2. Clone the Repository

1. Open **Command Prompt** or **PowerShell**.
2. Navigate to the folder where you want the project (e.g., Desktop, Documents, etc.):
   ```cmd
   cd C:\Users\YourUsername\Desktop
   ```
3. Clone the repository:
   ```cmd
   git clone https://github.com/nik123-py/Autonomous-Red-Teaming-AI.git
   ```
4. Navigate into the project folder:
   ```cmd
   cd Autonomous-Red-Teaming-AI\art-ai
   ```

> **Note:** All the following steps assume you are inside the `art-ai` directory.

---

## 3. Backend Setup

The backend is a **Python FastAPI** server. You need to create a virtual environment and install the dependencies.

### Step 3.1 — Navigate to the backend folder

```cmd
cd backend
```

### Step 3.2 — Create a Python virtual environment

```cmd
python -m venv venv
```

This creates a `venv/` folder inside `backend/` that contains an isolated Python installation.

### Step 3.3 — Activate the virtual environment

```cmd
.\venv\Scripts\activate
```

You should now see `(venv)` at the beginning of your terminal prompt, like this:
```
(venv) C:\...\art-ai\backend>
```

### Step 3.4 — Install Python dependencies

```cmd
pip install -r requirements.txt
```

This installs all required packages:
- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `torch` — PyTorch for ML models
- `openai` — LLM integration
- `python-dotenv` — Environment variable management
- And others listed in `requirements.txt`

> ⏳ **Note:** `torch` (PyTorch) is a large package (~2GB). The install may take several minutes depending on your internet speed.

### Step 3.5 — Configure environment variables

1. Copy the example environment file:
   ```cmd
   copy .env.example .env
   ```

2. Open the newly created `.env` file in a text editor and add your API key:
   ```env
   # Get your key at https://aistudio.google.com/apikey
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

3. Save and close the file.

### Step 3.6 — Verify backend starts

```cmd
.\venv\Scripts\python.exe main.py
```

You should see output similar to:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8003
```

Press `Ctrl+C` to stop the server. Backend setup is complete!

### Step 3.7 — Go back to project root

```cmd
cd ..
```

---

## 4. Frontend Setup

The frontend is a **React** application powered by **Vite**.

### Step 4.1 — Navigate to the frontend folder

```cmd
cd frontend
```

### Step 4.2 — Install Node.js dependencies

```cmd
npm install
```

This reads `package.json` and installs all required packages into `node_modules/`:
- `react` & `react-dom` — UI library
- `react-router-dom` — Page routing
- `reactflow` — Node graph visualization
- `recharts` — Charts and graphs
- `axios` — HTTP client for API calls

### Step 4.3 — Verify frontend starts

```cmd
npm run dev
```

You should see:
```
VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:3000/
```

Open `http://localhost:3000` in your browser to confirm. Press `Ctrl+C` to stop. Frontend setup is complete!

### Step 4.4 — Go back to project root

```cmd
cd ..
```

---

## 5. Vulnerable Lab Setup (Docker)

The vulnerable lab consists of **three Docker containers** that act as targets for the AI red teaming agent to scan and exploit.

> ⚠️ **Docker Desktop must be open and running** before proceeding.

### What Gets Installed

| Container | Image | Local Port | Description |
|-----------|-------|------------|-------------|
| **Juice Shop** | `bkimminich/juice-shop` | `3001` | OWASP vulnerable web app |
| **DVWA** | `vulnerables/web-dvwa` | `3002` | Damn Vulnerable Web Application |
| **Vulnerable API** | Custom (built locally) | `3003` | Intentionally vulnerable Flask API |

### Step 5.1 — Navigate to the lab folder

```cmd
cd lab
```

### Step 5.2 — Pull and start all containers

```cmd
docker compose up -d
```

> ⏳ **First-time note:** Docker will download the container images. This can take **5–10 minutes** depending on your internet speed. Subsequent starts will be instant.

### Step 5.3 — Verify containers are running

```cmd
docker ps
```

You should see three containers listed:
- `art-ai-juice-shop`
- `art-ai-dvwa`
- `art-ai-vulnerable-api`

### Step 5.4 — Verify access in your browser

Open each URL to confirm they load:

| Service | URL | What You Should See |
|---------|-----|---------------------|
| Juice Shop | [http://localhost:3001](http://localhost:3001) | OWASP Juice Shop storefront |
| DVWA | [http://localhost:3002](http://localhost:3002) | DVWA login page (admin / password) |
| Vulnerable API | [http://localhost:3003](http://localhost:3003) | JSON API response |

### Step 5.5 — Go back to project root

```cmd
cd ..
```

### Stopping the Lab (when done)

```cmd
cd lab
docker compose down
cd ..
```

### Alternative: Use the batch file

Instead of running Docker commands manually, you can double-click:
```
lab\start-vulnerable-lab.bat
```

---

## 6. Kali Linux Setup (Docker)

Kali Linux runs as a Docker container with a browser-accessible desktop via **noVNC**.

> ⚠️ **Docker Desktop must be open and running** before proceeding.

### About the Container

| Detail | Value |
|--------|-------|
| **Image** | `lscr.io/linuxserver/kali-linux:latest` |
| **Container Name** | `kali-web` |
| **Local Port** | `6080` |
| **Source** | [LinuxServer.io Docs](https://docs.linuxserver.io/images/docker-kali-linux/) |
| **Docker Hub** | [hub.docker.com/r/linuxserver/kali-linux](https://hub.docker.com/r/linuxserver/kali-linux) |

### Step 6.1 — Create and start the Kali container

```cmd
docker run -d --name kali-web -p 6080:3000 --shm-size=1g lscr.io/linuxserver/kali-linux:latest
```

> ⏳ **First-time note:** The Kali Linux image is **~1.5–2 GB**. The initial download may take several minutes.

### Step 6.2 — Verify the container is running

```cmd
docker ps -f name=kali-web
```

You should see the `kali-web` container with status `Up`.

### Step 6.3 — Access Kali Linux in your browser

Open your browser and navigate to:
```
http://localhost:6080
```

You should see a full Kali Linux desktop environment rendered directly in your browser.

### Stopping Kali (when done)

```cmd
docker stop kali-web
```

### Starting Kali again (next time)

```cmd
docker start kali-web
```

### Alternative: Use the batch file

Instead of running Docker commands manually, you can double-click:
```
start-kali-linux.bat
```

This script automatically starts the existing container, or creates a new one if it doesn't exist yet.

---

## 7. Running the Project

Once all setups (Sections 3–6) are complete, here is how to start the full project.

### Option A: Use the Batch Files (Recommended)

1. **Open Docker Desktop** and wait until the engine is running.

2. **Start the Vulnerable Lab:**
   - Double-click `lab\start-vulnerable-lab.bat`
   - Wait for the "Vulnerable lab is running" message.

3. **Start Kali Linux:**
   - Double-click `start-kali-linux.bat`
   - Wait for the "Accessible at" message.

4. **Start the Application (Backend + Frontend):**
   - Double-click `run-project.bat`
   - Two new terminal windows will open automatically — one for backend, one for frontend.

5. **Open the application:**
   - Navigate to **http://localhost:3000** in your browser.

### Option B: Start Everything Manually

Open **three separate terminals** and run:

**Terminal 1 — Backend:**
```cmd
cd art-ai\backend
.\venv\Scripts\activate
python main.py
```

**Terminal 2 — Frontend:**
```cmd
cd art-ai\frontend
npm run dev
```

**Terminal 3 — Docker (Lab + Kali):**
```cmd
cd art-ai\lab
docker compose up -d
cd ..
docker start kali-web
```

---

## 8. Port Reference & URLs

Quick reference for all services once everything is running:

| Service | URL | Port |
|---------|-----|------|
| **ART-AI Frontend** | [http://localhost:3000](http://localhost:3000) | `3000` |
| **ART-AI Backend API** | [http://localhost:8003](http://localhost:8003) | `8003` |
| **Backend API Docs (Swagger)** | [http://localhost:8003/docs](http://localhost:8003/docs) | `8003` |
| **Kali Linux Desktop** | [http://localhost:6080](http://localhost:6080) | `6080` |
| **Juice Shop** | [http://localhost:3001](http://localhost:3001) | `3001` |
| **DVWA** | [http://localhost:3002](http://localhost:3002) | `3002` |
| **Vulnerable API** | [http://localhost:3003](http://localhost:3003) | `3003` |

---

## 9. Troubleshooting

### "python is not recognized as an internal or external command"
- Python was not added to PATH during installation.
- **Fix:** Reinstall Python and check the _"Add python.exe to PATH"_ checkbox.

### "npm is not recognized"
- Node.js was not installed or not added to PATH.
- **Fix:** Reinstall Node.js from [nodejs.org](https://nodejs.org/).

### "docker: error during connect"
- Docker Desktop is not running.
- **Fix:** Open Docker Desktop and wait for the engine to fully start (the whale icon in the system tray should stop animating).

### "Port already in use" error
- Another process is using one of the required ports.
- **Fix:** Find and stop the process:
  ```cmd
  netstat -ano | findstr :PORT_NUMBER
  taskkill /PID <PID> /F
  ```

### "Container name kali-web already in use"
- The container was already created from a previous run.
- **Fix:** Remove the old container and create a new one:
  ```cmd
  docker rm kali-web
  docker run -d --name kali-web -p 6080:3000 --shm-size=1g lscr.io/linuxserver/kali-linux:latest
  ```

### Backend starts but frontend shows "Network Error"
- The backend may not be fully started yet.
- **Fix:** Wait a few seconds for the backend to initialize, then refresh the frontend page.

### "pip install" fails with build errors for torch
- **Fix:** Install the CPU-only version of PyTorch to avoid CUDA dependency issues:
  ```cmd
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install -r requirements.txt
  ```

### DVWA shows "Database Setup" after first access
- This is expected on first run — DVWA needs its database initialized.
- **Fix:** Click the **"Create / Reset Database"** button on the DVWA setup page, then log in with `admin` / `password`.

---

> **Need help?** Open an issue on the [GitHub repository](https://github.com/nik123-py/Autonomous-Red-Teaming-AI/issues).
