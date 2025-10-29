#!/bin/bash

echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Starting Split Services Architecture"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check if MongoDB is running
if ! nc -z localhost 27017 2>/dev/null; then
    echo "❌ MongoDB is not running on port 27017"
    echo "Please start MongoDB first:"
    echo "  docker run -d -p 27017:27017 --name mongodb \\"
    echo "    -e MONGO_INITDB_ROOT_USERNAME=admin \\"
    echo "    -e MONGO_INITDB_ROOT_PASSWORD=password123 \\"
    echo "    mongo:7"
    exit 1
fi

echo "✅ MongoDB is running"
echo ""

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo "Please export your OpenAI API key:"
    echo "  export OPENAI_API_KEY=your-key-here"
    exit 1
fi

echo "✅ OpenAI API key is set"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install dependencies for API service
echo "📦 Installing API service dependencies..."
cd fyi_widget_api
pip install -q -r requirements.txt
cd ..

# Install dependencies for worker service
echo "📦 Installing worker service dependencies..."
cd fyi_widget_worker_service
pip install -q -r requirements.txt
cd ..

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "🎯 Starting Services"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Kill any existing processes
pkill -f "fyi_widget_api.api.main" 2>/dev/null
pkill -f "fyi_widget_worker_service.run_worker" 2>/dev/null

# Start API service in background
echo "🌐 Starting API Service on port 8005..."
cd fyi_widget_api
python run_server.py > ../fyi_widget_api.log 2>&1 &
API_PID=$!
cd ..

sleep 3

# Check if API service started
if ps -p $API_PID > /dev/null; then
    echo "✅ API Service started (PID: $API_PID)"
else
    echo "❌ API Service failed to start"
    cat fyi_widget_api.log
    exit 1
fi

# Start Worker service in background
echo "⚙️  Starting Worker Service..."
cd fyi_widget_worker_service
python run_worker.py > ../fyi_widget_worker_service.log 2>&1 &
WORKER_PID=$!
cd ..

sleep 3

# Check if Worker service started
if ps -p $WORKER_PID > /dev/null; then
    echo "✅ Worker Service started (PID: $WORKER_PID)"
else
    echo "❌ Worker Service failed to start"
    cat fyi_widget_worker_service.log
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ ALL SERVICES RUNNING!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "API Service:"
echo "  URL: http://localhost:8005"
echo "  Docs: http://localhost:8005/docs"
echo "  Health: http://localhost:8005/health"
echo "  Logs: tail -f fyi_widget_api.log"
echo "  PID: $API_PID"
echo ""
echo "Worker Service:"
echo "  Logs: tail -f fyi_widget_worker_service.log"
echo "  PID: $WORKER_PID"
echo ""
echo "To stop services:"
echo "  kill $API_PID $WORKER_PID"
echo "  or: pkill -f 'fyi_widget_api|fyi_widget_worker_service'"
echo ""
echo "════════════════════════════════════════════════════════════════════"

