#!/bin/bash

###############################################################################
# Deploy Databases (MongoDB + PostgreSQL) Independently
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

print_header "🗄️  Deploying Databases"

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found!"
    if [ -f env.production.example ]; then
        print_info "Creating .env from env.production.example..."
        cp env.production.example .env
        chmod 600 .env
        print_warning "⚠️  IMPORTANT: Edit .env file and update all passwords!"
        exit 1
    else
        print_error "env.production.example not found. Please create .env manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up any existing network that might cause conflicts
print_info "Checking for existing network..."
if docker network inspect blog-qa-network > /dev/null 2>&1; then
    print_warning "Existing network found. Checking if it's safe to remove..."
    # Only remove if no containers are using it (except stopped ones)
    NETWORK_CONTAINERS=$(docker network inspect blog-qa-network --format '{{len .Containers}}' 2>/dev/null || echo "0")
    if [ "$NETWORK_CONTAINERS" = "0" ]; then
        print_info "Removing existing network to avoid conflicts..."
        docker network rm blog-qa-network 2>/dev/null || true
    else
        print_warning "Network is in use. Will try to use existing network."
    fi
fi

print_info "Docker Compose will create/manage the network automatically"

# Deploy MongoDB
print_header "📦 Deploying MongoDB"
docker-compose -f docker-compose.mongodb.yml up -d

# Wait for MongoDB to be healthy
print_info "⏳ Waiting for MongoDB to be healthy..."
sleep 10

# Check MongoDB status
if docker ps | grep -q blog-qa-mongodb; then
    print_success "MongoDB is running"
    docker ps | grep mongodb
else
    print_error "MongoDB failed to start"
    docker logs blog-qa-mongodb --tail 20
    exit 1
fi

# Deploy PostgreSQL
print_header "📦 Deploying PostgreSQL"
docker-compose -f docker-compose.postgres.yml up -d

# Wait for PostgreSQL to be healthy
print_info "⏳ Waiting for PostgreSQL to be healthy..."
sleep 10

# Check PostgreSQL status
if docker ps | grep -q blog-qa-postgres; then
    print_success "PostgreSQL is running"
    docker ps | grep postgres
else
    print_error "PostgreSQL failed to start"
    docker logs blog-qa-postgres --tail 20
    exit 1
fi

# Test connections
print_header "🧪 Testing Database Connections"

# Test MongoDB
print_info "Testing MongoDB connection..."
if docker exec blog-qa-mongodb mongosh --eval "db.runCommand('ping')" --quiet > /dev/null 2>&1; then
    print_success "MongoDB connection: OK"
else
    print_warning "MongoDB connection: Failed (may still be initializing)"
fi

# Test PostgreSQL
print_info "Testing PostgreSQL connection..."
if docker exec blog-qa-postgres pg_isready -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; then
    print_success "PostgreSQL connection: OK"
else
    print_warning "PostgreSQL connection: Failed (may still be initializing)"
fi

print_header "✅ Databases Deployed Successfully!"

echo ""
echo "📊 Service Status:"
docker ps | grep -E "mongodb|postgres"

echo ""
echo "🔗 Connection Info:"
echo "  MongoDB:    mongodb://${MONGODB_USERNAME:-admin}:${MONGODB_PASSWORD}@localhost:27017/${DATABASE_NAME:-blog_qa_db}"
echo "  PostgreSQL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB:-blog_qa_publishers}"
echo ""
echo "📝 Useful Commands:"
echo "  View MongoDB logs:  docker logs -f blog-qa-mongodb"
echo "  View Postgres logs: docker logs -f blog-qa-postgres"
echo "  Stop databases:     docker-compose -f docker-compose.mongodb.yml down"
echo "                      docker-compose -f docker-compose.postgres.yml down"
echo ""


