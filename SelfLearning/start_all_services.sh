#!/bin/bash

###############################################################################
# Quick Start Script for Blog Q&A System
# This script starts all services: MongoDB, PostgreSQL, API, and Worker
###############################################################################

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Starting Blog Q&A System - All Services"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Loaded configuration from .env file"
elif [ -f "env.example" ] && [ ! -f ".env" ]; then
    echo "ℹ️  No .env file found. Creating from env.example..."
    echo "   Please edit .env and add your OpenAI API key"
    echo ""
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-key-here" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY is not configured"
    echo "   The system will start but LLM features won't work."
    echo ""
    echo "   To set it up:"
    echo "   1. Copy: cp env.example .env"
    echo "   2. Edit .env and add your API key"
    echo "   3. Re-run this script"
    echo ""
    echo "   OR export it directly:"
    echo "   export OPENAI_API_KEY='sk-your-key-here'"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Start all services with docker-compose
echo "📦 Starting all services with Docker Compose..."
echo ""
# Pull required images first to avoid timeout issues
echo "📥 Pulling Docker images..."
docker-compose -f docker-compose.split-services.yml pull mongodb postgres mongo-express pgadmin || true

# Start all services
docker-compose -f docker-compose.split-services.yml up -d

# Ensure admin UIs are started (they might fail silently during initial up)
echo "🔧 Ensuring admin UIs are running..."
docker-compose -f docker-compose.split-services.yml up -d mongo-express pgadmin

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "📊 Service Status"
echo "════════════════════════════════════════════════════════════════════"
docker-compose -f docker-compose.split-services.yml ps

# Test API health
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "🏥 Health Check"
echo "════════════════════════════════════════════════════════════════════"
if curl -s http://localhost:8005/health > /dev/null; then
    echo "✅ API Service: http://localhost:8005"
    curl -s http://localhost:8005/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8005/health
else
    echo "⚠️  API Service: Not responding yet (may still be starting)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ ALL SERVICES STARTED!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📚 Service URLs:"
echo ""
echo "   Application:"
echo "   • API Service:    http://localhost:8005"
echo "   • API Docs:       http://localhost:8005/docs"
echo "   • Health Check:   http://localhost:8005/health"
echo ""
echo "   Database UIs (Web Interfaces):"
echo "   • Mongo Express:  http://localhost:8081 (admin/password123)"
echo "   • pgAdmin:        http://localhost:5050 (admin@admin.com/admin123)"
echo ""
echo "   Direct Database Connections:"
echo "   • MongoDB:        mongodb://admin:password123@localhost:27017"
echo "   • PostgreSQL:     postgresql://postgres:postgres@localhost:5432/blog_qa_publishers"
echo ""
echo "📋 Useful Commands:"
echo "   • View logs:      docker-compose -f docker-compose.split-services.yml logs -f"
echo "   • Stop services:  docker-compose -f docker-compose.split-services.yml down"
echo "   • Restart:        docker-compose -f docker-compose.split-services.yml restart"
echo ""
echo "📖 Full Documentation: See HOW_TO_RUN.md"
echo ""
echo "════════════════════════════════════════════════════════════════════"

