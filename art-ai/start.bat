@echo off
REM ART-AI Quick Start Script for Windows

echo === ART-AI: Autonomous Red Team AI ===
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker first.
    exit /b 1
)

REM Start vulnerable lab
echo Starting vulnerable lab...
cd lab
docker-compose up -d
cd ..

echo.
echo Vulnerable lab started!
echo   - Juice Shop: http://localhost:3001
echo   - DVWA: http://localhost:3002
echo   - Vulnerable API: http://localhost:3003
echo.

REM Check if backend dependencies are installed
if not exist "backend\venv" (
    echo Setting up backend...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
)

REM Check if frontend dependencies are installed
if not exist "frontend\node_modules" (
    echo Setting up frontend...
    cd frontend
    call npm install
    cd ..
)

echo.
echo Setup complete!
echo.
echo To start the system:
echo   1. Backend: cd backend ^&^& venv\Scripts\activate ^&^& python main.py
echo   2. Frontend: cd frontend ^&^& npm run dev
echo.
echo Then open http://localhost:3000 in your browser
pause

