@echo off
REM Start ART-AI Vulnerable Lab (Juice Shop, DVWA, Vulnerable API)
cd /d "%~dp0"

echo.
echo === ART-AI Vulnerable Lab ===
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting containers...
docker compose up -d

if errorlevel 1 (
    echo.
    echo Failed to start. Try: docker-compose up -d
    pause
    exit /b 1
)

echo.
echo === Vulnerable lab is running ===
echo   Juice Shop:     http://localhost:3001
echo   DVWA:           http://localhost:3002
echo   Vulnerable API: http://localhost:3003
echo.
pause
