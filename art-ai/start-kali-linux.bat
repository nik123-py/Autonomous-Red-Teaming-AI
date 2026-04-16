@echo off
title Start Kali Linux Container
echo === Starting Kali Linux Docker Container ===

echo Starting 'kali-web'...
docker start kali-web

if %ERRORLEVEL% neq 0 (
    echo.
    echo Container 'kali-web' not found or failed to start.
    echo Attempting to create and start a new container...
    docker run -d --name kali-web -p 6080:3000 --shm-size=1g lscr.io/linuxserver/kali-linux:latest
)

echo.
echo === Kali Linux Desktop ===
echo Accessible at: http://localhost:6080
echo.
echo Press any key to exit.
pause >nul
