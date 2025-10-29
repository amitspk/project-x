#!/bin/bash

###############################################################################
# Deploy API Service Independently
# Requires: MongoDB and PostgreSQL to be running
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header "🚀 Deploying API Service"

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found!"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if databases are running
print_info "Checking database services..."

if ! docker ps | grep -q blog-qa-mongodb; then
    print_error "MongoDB is not running!"
    print_info "Start it first: docker-compose -f docker-compose.mongodb.yml up -d"
    print_info "Or run: ./scripts/deploy-databases.sh"
    exit 1
fi

if ! docker ps | grep -q blog-qa-postgres; then
    print_error "PostgreSQL is not running!"
    print_info "Start it first: docker-compose -f docker-compose.postgres.yml up -d"
    print_info "Or run: ./scripts/deploy-databases.sh"
    exit 1
fi

print_success "Databases are running"

# Ensure network exists
print_info "Ensuring Docker network exists..."
docker network create blog-qa-network 2>/dev/null || print_info "Network already exists"

# Build API service
print_header "🔨 Building API Service"
docker-compose -f docker-compose.api.yml build

# Start API service
print_header "🚀 Starting API Service"
docker-compose -f docker-compose.api.yml up -d

# Wait for API to be healthy
print_info "⏳ Waiting for API service to start..."
sleep 15

# Check API status
print_header "🧪 Testing API Service"

if docker ps | grep -q fyi-widget-api; then
    print_success "API container is running"
else
    print_error "API container failed to start"
    docker logs fyi-widget-api --tail 30
    exit 1
fi

# Test API health endpoint
print_info "Testing API health endpoint..."
if curl -f http://localhost:8005/health > /dev/null 2>&1; then
    print_success "API is responding!"
    echo ""
    curl -s http://localhost:8005/health | head -10
else
    print_warning "API not responding yet, give it a few more seconds..."
    print_info "Check logs: docker logs -f fyi-widget-api"
fi

print_header "✅ API Service Deployed!"

echo ""
echo "📊 Service Status:"
docker ps | grep api

echo ""
echo "🔗 API URLs:"
echo "  API:      http://localhost:8005"
echo "  Docs:     http://localhost:8005/docs"
echo "  Health:   http://localhost:8005/health"
echo ""
echo "📝 Useful Commands:"
echo "  View logs:    docker logs -f fyi-widget-api"
echo "  Restart:      docker-compose -f docker-compose.api.yml restart"
echo "  Stop:         docker-compose -f docker-compose.api.yml down"
echo "  Update:       docker-compose -f docker-compose.api.yml build && docker-compose -f docker-compose.api.yml up -d"
echo ""


