#!/bin/bash

echo "🚀 Starting Backend Services..."

# Change to backend directory
cd app/backend

# Start supplier API in background
echo "📊 Starting Supplier API on port 8001..."
python supplier_api.py &
SUPPLIER_PID=$!

# Wait a moment
sleep 2

# Start main API in background
echo "🏭 Starting Main API on port 8000..."
python backend_api.py &
MAIN_PID=$!

echo "✅ Both APIs started!"
echo "📊 Supplier API: http://localhost:8001"
echo "🏭 Main API: http://localhost:8000"
echo "🌐 Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Function to clean up background processes
cleanup() {
    echo "🛑 Stopping services..."
    kill $SUPPLIER_PID $MAIN_PID 2>/dev/null
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Wait for background processes
wait