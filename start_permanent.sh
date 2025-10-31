#!/bin/bash

echo "🚀 Starting Falcon Chatbot with PERMANENT Domain (Robust Version)..."

# Kill any existing processes
pkill -f "uvicorn"
pkill -f "ngrok"

cd /Users/mac/Desktop/Techgropse/FalconFullstack/backend

# Set the correct Python environment
eval "$(pyenv init -)"
pyenv shell 3.11.8

# Start backend with proper error handling
echo "Starting FastAPI backend..."
nohup python -c "
import sys
import os
sys.path.append(os.getcwd())
from main import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(
        'main:app', 
        host='0.0.0.0', 
        port=8000, 
        log_level='info',
        access_log=True,
        reload=False
    )
" > backend.log 2>&1 &
BACKEND_PID=$!

echo "Backend starting with PID: $BACKEND_PID"
sleep 15  # Give more time to start

# Check if backend started successfully
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Backend is running and stable!"
    
    # Start ngrok tunnel
    echo "Starting Ngrok tunnel with permanent domain..."
    nohup ngrok http --domain=nathaly-purest-ariella.ngrok-free.dev 8000 > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    echo "Tunnel starting with PID: $TUNNEL_PID"
    echo "Waiting for tunnel to establish..."
    sleep 10
    
    echo "🎯 Your PERMANENT URL: https://nathaly-purest-ariella.ngrok-free.dev"
    echo ""
    
    # Test multiple times to ensure stability
    echo "🧪 Testing backend stability..."
    for i in {1..3}; do
        echo "Test $i: $(curl -s https://nathaly-purest-ariella.ngrok-free.dev/)"
        sleep 2
    done
    
    echo ""
    echo "✅ PERMANENT SETUP COMPLETE!"
    echo "Share this FOREVER with testers:"
    echo "POST https://nathaly-purest-ariella.ngrok-free.dev/api/chat/"
    echo ""
    echo "📋 Useful commands:"
    echo "View backend logs: tail -f backend.log"
    echo "View tunnel logs: tail -f tunnel.log"
    echo "Check if running: ps aux | grep uvicorn"
    echo "Stop services: pkill -f 'uvicorn'; pkill -f 'ngrok'"
else
    echo "❌ Backend failed to start. Check backend.log for errors:"
    tail -30 backend.log
    echo ""
    echo "🔍 Checking Python environment:"
    python -c "import sys; print('Python path:', sys.executable)"
    python -c "import uvicorn; print('Uvicorn available')"
fi