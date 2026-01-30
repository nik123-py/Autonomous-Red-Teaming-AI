@echo off
REM ART-AI - Run Backend + Frontend (whole project)
title ART-AI Launcher
cd /d "%~dp0"

echo.
echo === ART-AI: Starting Backend and Frontend ===
echo.

REM Start Backend in new window
echo Starting Backend server (port 8000)...
start "ART-AI Backend" cmd /k "cd /d "%~dp0backend" && if exist venv\Scripts\python.exe (venv\Scripts\python.exe main.py) else (python main.py)"

REM Wait a moment so backend can bind first
ping 127.0.0.1 -n 4 >nul 2>&1

REM Start Frontend in new window
echo Starting Frontend server (port 5173)...
start "ART-AI Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo === Servers starting in separate windows ===
echo.
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173  (or http://localhost:3000)
echo.
echo Close this window or press any key to exit launcher (servers keep running).
pause >nul
