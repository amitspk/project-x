#!/bin/bash

###############################################################################
# Deploy Worker Service Independently
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

print_header "⚙️  Deploying Worker Service"

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

# Build worker service
print_header "🔨 Building Worker Service"
docker-compose -f docker-compose.worker.yml build

# Start worker service
print_header "⚙️  Starting Worker Service"
docker-compose -f docker-compose.worker.yml up -d

# Wait for worker to start
print_info "⏳ Waiting for worker service to start..."
sleep 10

# Check worker status
print_header "🧪 Checking Worker Service"

if docker ps | grep -q fyi-widget-worker-service; then
    print_success "Worker container is running"
else
    print_error "Worker container failed to start"
    docker logs fyi-widget-worker-service --tail 30
    exit 1
fi

# Show worker logs
print_info "Recent worker logs:"
docker logs fyi-widget-worker-service --tail 20

print_header "✅ Worker Service Deployed!"

echo ""
echo "📊 Service Status:"
docker ps | grep fyi-widget-worker-service

echo ""
echo "📝 Useful Commands:"
echo "  View logs:    docker logs -f fyi-widget-worker-service"
echo "  Restart:      docker-compose -f docker-compose.worker.yml restart"
echo "  Stop:         docker-compose -f docker-compose.worker.yml down"
echo "  Scale:        docker-compose -f docker-compose.worker.yml up -d --scale worker-service=3"
echo "  Update:       docker-compose -f docker-compose.worker.yml build && docker-compose -f docker-compose.worker.yml up -d"
echo ""


