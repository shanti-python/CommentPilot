#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo "   Instagram Comment Automation Platform Launcher        "
echo "=========================================================="

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null
then
    echo "⚠️  Warning: redis-server is not running. Background Celery workers will fail."
    echo "Please start redis-server or run: sudo service redis-server start"
fi

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID $CELERY_PID 2>/dev/null || true
    exit
}
trap cleanup SIGINT SIGTERM EXIT

# Start Backend
echo "🚀 Starting FastAPI Backend (Port 8000)..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start Celery Background Worker
echo "⚙️ Starting Celery Background Worker..."
celery -A app.core.cel_app:celery_app worker --loglevel=info &
CELERY_PID=$!

# Start Frontend
echo "💻 Starting Vite React Frontend (Port 5173)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "=========================================================="
echo "🎯 Dashboard ready: http://localhost:5173"
echo "⚙️  API docs: http://localhost:8000/docs"
echo "=========================================================="

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID $CELERY_PID
