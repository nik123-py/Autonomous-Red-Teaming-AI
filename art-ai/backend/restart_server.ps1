# Restart ART-AI Backend Server
Write-Host "=== Restarting ART-AI Backend Server ===" -ForegroundColor Cyan

# Kill existing server
$processes = Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Where-Object {
    $_.Path -like "*venv*" -or (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess -eq $_.Id
}
if ($processes) {
    Write-Host "Stopping existing server processes..." -ForegroundColor Yellow
    $processes | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Activate venv and start server
Write-Host "Starting backend server..." -ForegroundColor Green
Set-Location $PSScriptRoot
if (Test-Path "venv\Scripts\activate.ps1") {
    & "venv\Scripts\python.exe" main.py
} else {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
}

