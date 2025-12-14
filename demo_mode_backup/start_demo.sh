#!/bin/bash
# Quick start script for demo mode

echo "🚀 Starting Enterprise Document Intelligence Platform - DEMO MODE"
echo "================================================================"
echo ""
echo "📍 Mode: In-Memory Storage (No Database Required)"
echo "✅ Quick testing without PostgreSQL"
echo "⚠️  Data will be lost on restart"
echo ""
echo "================================================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create directories
mkdir -p uploads logs chromadb_data
echo "✅ Created directories"
echo ""

# Start backend
echo "🔧 Starting backend server on port 8000..."
echo ""
export PATH=$PATH:/Users/benchen1981/Library/Python/3.9/bin
cd backend
python3 -m uvicorn main_demo:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend is running!"
else
    echo "⚠️  Backend may still be starting..."
fi

echo ""
echo "================================================================"
echo "✅ DEMO MODE READY!"
echo "================================================================"
echo ""
echo "🌐 Backend API: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
echo "To start frontend (in another terminal):"
echo "  cd frontend"
echo "  python3 -m streamlit run app.py"
echo ""
echo "To stop: Press Ctrl+C"
echo "================================================================"
echo ""

# Wait for user interrupt
wait $BACKEND_PID
