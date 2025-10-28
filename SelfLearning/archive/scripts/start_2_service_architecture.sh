#!/bin/bash

# Start 2-Service Architecture
# This script starts the consolidated architecture locally for testing

echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Starting 2-Service Architecture"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python 3 found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo "✅ Docker found"

# Check OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY environment variable is not set"
    echo ""
    echo "Please set it:"
    echo "  export OPENAI_API_KEY=your-api-key-here"
    exit 1
fi
echo "✅ OpenAI API key configured"

echo ""
echo "────────────────────────────────────────────────────────────────────"
echo "Starting infrastructure..."
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Start MongoDB
echo "Starting MongoDB..."
if docker ps | grep -q blog-mongodb; then
    echo "  MongoDB already running"
else
    docker run -d \
        --name blog-mongodb \
        -p 27017:27017 \
        mongo:7.0 \
        > /dev/null 2>&1
    
    echo "  Waiting for MongoDB to be ready..."
    sleep 3
    echo "✅ MongoDB started on port 27017"
fi

# Start Redis
echo "Starting Redis..."
if docker ps | grep -q blog-redis; then
    echo "  Redis already running"
else
    docker run -d \
        --name blog-redis \
        -p 6379:6379 \
        redis:7-alpine \
        > /dev/null 2>&1
    
    echo "✅ Redis started on port 6379"
fi

echo ""
echo "────────────────────────────────────────────────────────────────────"
echo "Installing dependencies..."
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Install Content Service dependencies
echo "Installing Content Processing Service dependencies..."
cd content_processing_service
pip install -q -r requirements.txt
cd ..
echo "✅ Content Service dependencies installed"

# Install API Gateway dependencies (if needed)
echo "Checking API Gateway dependencies..."
if [ -f "blog_manager/requirements.txt" ]; then
    cd blog_manager
    pip install -q -r requirements.txt 2>/dev/null || true
    cd ..
fi
echo "✅ API Gateway dependencies ready"

echo ""
echo "────────────────────────────────────────────────────────────────────"
echo "Starting services..."
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Set environment variables
export MONGODB_URL=mongodb://localhost:27017
export REDIS_URL=redis://localhost:6379
export PORT=8005

echo "Starting Content Processing Service (port 8005)..."
echo "  (This will run in the foreground - open another terminal for API Gateway)"
echo ""
echo "To start API Gateway in another terminal:"
echo "  cd blog_manager"
echo "  export CONTENT_SERVICE_URL=http://localhost:8005"
echo "  export REDIS_URL=redis://localhost:6379"
echo "  python run_server.py"
echo ""
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Run Content Service
python -m content_processing_service.run_server

