#!/bin/bash

# MongoDB Docker Setup Script for SelfLearning Project
# This script sets up MongoDB with Docker Compose

set -e  # Exit on any error

echo "🚀 Setting up MongoDB for SelfLearning Project"
echo "=" * 50

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "💡 Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Determine which docker compose command to use
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

echo "✅ Docker and Docker Compose are available"

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in current directory"
    echo "💡 Make sure you're in the SelfLearning project directory"
    exit 1
fi

echo "📁 Found docker-compose.yml"

# Create necessary directories
echo "📂 Creating necessary directories..."
mkdir -p init
mkdir -p data/mongodb

# Set permissions for MongoDB data directory
chmod 755 data/mongodb

echo "🐳 Starting MongoDB containers..."

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
$DOCKER_COMPOSE down

# Start the containers
echo "🚀 Starting MongoDB and Mongo Express..."
$DOCKER_COMPOSE up -d

# Wait for MongoDB to be ready
echo "⏳ Waiting for MongoDB to be ready..."
sleep 10

# Check if containers are running
if [ "$(docker ps -q -f name=selflearning_mongodb)" ]; then
    echo "✅ MongoDB container is running"
else
    echo "❌ MongoDB container failed to start"
    echo "📋 Container logs:"
    docker logs selflearning_mongodb
    exit 1
fi

if [ "$(docker ps -q -f name=selflearning_mongo_express)" ]; then
    echo "✅ Mongo Express container is running"
else
    echo "⚠️  Mongo Express container may not be running"
fi

# Test MongoDB connection
echo "🔍 Testing MongoDB connection..."
if docker exec selflearning_mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "✅ MongoDB is responding to connections"
else
    echo "❌ MongoDB connection test failed"
    exit 1
fi

echo ""
echo "🎉 MongoDB setup completed successfully!"
echo "=" * 50
echo ""
echo "📊 Connection Information:"
echo "   MongoDB URL: mongodb://admin:password123@localhost:27017/blog_ai_db"
echo "   Database: blog_ai_db"
echo "   Username: admin"
echo "   Password: password123"
echo ""
echo "🌐 Web Interface:"
echo "   Mongo Express: http://localhost:8081"
echo "   Login: admin / password123"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs: docker logs selflearning_mongodb"
echo "   Stop containers: $DOCKER_COMPOSE down"
echo "   Restart containers: $DOCKER_COMPOSE restart"
echo "   Connect to MongoDB: docker exec -it selflearning_mongodb mongosh -u admin -p password123"
echo ""
echo "📝 Next Steps:"
echo "   1. Open http://localhost:8081 to view the database"
echo "   2. Install Python MongoDB driver: pip install pymongo"
echo "   3. Use the connection string in your Python applications"
echo ""
