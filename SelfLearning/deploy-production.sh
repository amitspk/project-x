#!/bin/bash

###############################################################################
# Production Deployment Script
# Quick deployment script for VPS production setup
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header "🚀 Production Deployment Script"

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found!"
    if [ -f env.production.example ]; then
        print_info "Creating .env from env.production.example..."
        cp env.production.example .env
        chmod 600 .env
        print_warning "⚠️  IMPORTANT: Edit .env file and update all passwords and API keys!"
        print_info "Run: nano .env"
        exit 1
    else
        print_error "env.production.example not found. Please create .env manually."
        exit 1
    fi
fi

# Validate docker-compose.production.yml exists
if [ ! -f docker-compose.production.yml ]; then
    print_error "docker-compose.production.yml not found!"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_info "See PRODUCTION_DEPLOYMENT_GUIDE.md for installation instructions."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_header "📦 Building Docker Images"
docker-compose -f docker-compose.production.yml build

print_header "🚀 Starting Services"
docker-compose -f docker-compose.production.yml up -d

print_header "⏳ Waiting for Services to Start"
sleep 10

print_header "✅ Verifying Deployment"

# Check service status
print_info "Service Status:"
docker-compose -f docker-compose.production.yml ps

# Test API health
print_info "Testing API health endpoint..."
if curl -f http://localhost:8005/health &> /dev/null; then
    print_success "API is responding!"
    curl -s http://localhost:8005/health | head -20
else
    print_warning "API not responding yet. Give it a few more seconds..."
    print_info "Check logs: docker-compose -f docker-compose.production.yml logs api-service"
fi

print_header "📊 Deployment Summary"
echo ""
print_success "Services deployed successfully!"
echo ""
print_info "Next Steps:"
echo "  1. Verify all services: docker-compose -f docker-compose.production.yml ps"
echo "  2. Check logs: docker-compose -f docker-compose.production.yml logs -f"
echo "  3. Setup Nginx reverse proxy (see PRODUCTION_DEPLOYMENT_GUIDE.md)"
echo "  4. Configure SSL with Let's Encrypt"
echo "  5. Setup automated backups"
echo ""
print_info "View API docs: http://localhost:8005/docs"
print_info "View logs: docker-compose -f docker-compose.production.yml logs -f"
echo ""

