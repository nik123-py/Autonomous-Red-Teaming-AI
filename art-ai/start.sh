#!/bin/bash

# ART-AI Quick Start Script

echo "=== ART-AI: Autonomous Red Team AI ==="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start vulnerable lab
echo "Starting vulnerable lab..."
cd lab
docker-compose up -d
cd ..

echo ""
echo "Vulnerable lab started!"
echo "  - Juice Shop: http://localhost:3001"
echo "  - DVWA: http://localhost:3002"
echo "  - Vulnerable API: http://localhost:3003"
echo ""

# Check if backend dependencies are installed
if [ ! -d "backend/venv" ]; then
    echo "Setting up backend..."
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "Setting up frontend..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "Setup complete!"
echo ""
echo "To start the system:"
echo "  1. Backend: cd backend && source venv/bin/activate && python main.py"
echo "  2. Frontend: cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser"

