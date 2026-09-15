#!/bin/bash
cd "$(dirname "$0")"

echo "🚀 Starting DeepCore Services in background..."

# Source .env if present so child processes inherit all API keys
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Kill any existing processes running on ports 8000 or 5173
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null

# Start FastAPI Backend
nohup .venv/bin/uvicorn deepcore2.api.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &
BACKEND_PID=$!

# Start Vite Frontend
nohup npm --prefix shell run dev -- --host 0.0.0.0 > vite.log 2>&1 &
FRONTEND_PID=$!

sleep 2

echo "✅ DeepCore is running in the background!"
echo "   - Frontend UI:  http://localhost:5173 (logs: vite.log)"
echo "   - Backend API:  http://127.0.0.1:8000 (logs: uvicorn.log)"
