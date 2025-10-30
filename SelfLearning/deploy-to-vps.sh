#!/bin/bash

###############################################################################
# Blog Q&A VPS Deployment Script
# This script automates the deployment of the Blog Q&A system to a VPS
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Check if running on VPS or local machine
if [ "$1" == "--local" ]; then
    MODE="local"
    print_header "🚀 VPS Deployment - Local Mode"
    print_info "This will prepare deployment files on your local machine"
else
    MODE="vps"
    print_header "🚀 VPS Deployment - VPS Mode"
    print_info "This will set up your VPS for deployment"
fi

###############################################################################
# LOCAL MODE - Prepare files for deployment
###############################################################################
if [ "$MODE" == "local" ]; then
    print_header "📦 Preparing Deployment Files"
    
    # Create production docker-compose
    print_info "Creating production docker-compose file..."
    cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: fyi-widget-mongodb-prod
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGODB_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD}
      MONGO_INITDB_DATABASE: ${DATABASE_NAME}
    volumes:
      - mongodb_data:/data/db
    networks:
      - fyi-widget-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:16-alpine
    container_name: fyi-widget-postgres-prod
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fyi-widget-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  api-service:
    build:
      context: .
      dockerfile: fyi_widget_api/Dockerfile
    container_name: fyi-widget-api-prod
    restart: always
    ports:
      - "8005:8005"
    environment:
      MONGODB_URL: ${MONGODB_URL}
      MONGODB_USERNAME: ${MONGODB_USERNAME}
      MONGODB_PASSWORD: ${MONGODB_PASSWORD}
      DATABASE_NAME: ${DATABASE_NAME}
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL}
      ADMIN_API_KEY: ${ADMIN_API_KEY}
      API_SERVICE_PORT: ${API_SERVICE_PORT}
    depends_on:
      mongodb:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - fyi-widget-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker-service:
    build:
      context: .
      dockerfile: fyi_widget_worker_service/Dockerfile
    container_name: fyi-widget-worker-service-prod
    restart: always
    environment:
      MONGODB_URL: ${MONGODB_URL}
      MONGODB_USERNAME: ${MONGODB_USERNAME}
      MONGODB_PASSWORD: ${MONGODB_PASSWORD}
      DATABASE_NAME: ${DATABASE_NAME}
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL}
      WORKER_POLL_INTERVAL: ${WORKER_POLL_INTERVAL}
    depends_on:
      mongodb:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - fyi-widget-network

networks:
  fyi-widget-network:
    driver: bridge

volumes:
  mongodb_data:
  postgres_data:
EOF
    print_success "Production docker-compose created"
    
    # Create .env.production template
    print_info "Creating .env.production template..."
    cat > .env.production.template << 'EOF'
# Production Environment Configuration
# Copy this to .env and fill in your values

# MongoDB
MONGODB_URL=mongodb://mongodb:27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=CHANGE_THIS_SECURE_MONGODB_PASSWORD

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=blog_qa_publishers
POSTGRES_USER=admin
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_POSTGRES_PASSWORD

# OpenAI
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_API_KEY_HERE
OPENAI_MODEL=gpt-4o-mini

# API Service
API_SERVICE_PORT=8005
ADMIN_API_KEY=CHANGE_THIS_TO_SECURE_ADMIN_KEY

# Worker Service
WORKER_POLL_INTERVAL=10
DATABASE_NAME=blog_qa_db

# CORS (add your actual domains)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
EOF
    print_success ".env.production.template created"
    
    print_header "📋 Next Steps"
    echo "1. Transfer files to VPS:"
    echo "   rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \\"
    echo "     ./ username@YOUR_VPS_IP:/home/username/SelfLearning/"
    echo ""
    echo "2. SSH into VPS and run:"
    echo "   ssh username@YOUR_VPS_IP"
    echo "   cd /home/username/SelfLearning"
    echo "   ./deploy-to-vps.sh"
    echo ""
    print_success "Local preparation complete!"
    exit 0
fi

###############################################################################
# VPS MODE - Set up VPS
###############################################################################

print_header "1️⃣  System Update"
print_info "Updating system packages..."
sudo apt update
sudo apt upgrade -y
print_success "System updated"

print_header "2️⃣  Installing Docker"
if command -v docker &> /dev/null; then
    print_info "Docker already installed ($(docker --version))"
else
    print_info "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_success "Docker installed"
fi

print_header "3️⃣  Installing Docker Compose"
if command -v docker-compose &> /dev/null; then
    print_info "Docker Compose already installed ($(docker-compose --version))"
else
    print_info "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed"
fi

print_header "4️⃣  Installing Additional Tools"
print_info "Installing git, jq, nginx..."
sudo apt install -y git jq nginx certbot python3-certbot-nginx
print_success "Additional tools installed"

print_header "5️⃣  Configuring Environment"
if [ ! -f .env ]; then
    if [ -f .env.production.template ]; then
        print_info "Creating .env from template..."
        cp .env.production.template .env
        print_warning "IMPORTANT: Edit .env file and update all passwords and API keys!"
        print_info "Run: nano .env"
    else
        print_error ".env.production.template not found"
        print_info "Please create .env file manually"
    fi
else
    print_info ".env file already exists"
fi

print_header "6️⃣  Configuring Firewall"
print_info "Setting up UFW firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8005/tcp  # API (optional, if not using nginx)
print_success "Firewall configured"

print_header "7️⃣  Building Application"
if [ -f docker-compose.production.yml ]; then
    print_info "Building Docker images..."
    docker-compose -f docker-compose.production.yml build
    print_success "Build complete"
else
    print_error "docker-compose.production.yml not found"
    exit 1
fi

print_header "8️⃣  Starting Services"
print_info "Starting all services..."
docker-compose -f docker-compose.production.yml up -d
print_success "Services started"

print_header "9️⃣  Verifying Deployment"
sleep 5
print_info "Checking container status..."
docker-compose -f docker-compose.production.yml ps

print_info "Testing API health..."
if curl -f http://localhost:8005/health &> /dev/null; then
    print_success "API is responding!"
else
    print_warning "API not responding yet, give it a few more seconds..."
fi

print_header "✅ Deployment Complete!"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "📝 View Logs:"
echo "   docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔍 Check API:"
echo "   curl http://localhost:8005/health"
echo "   curl http://localhost:8005/docs"
echo ""
echo "🌐 Next Steps:"
echo "   1. Edit .env file and update passwords/API keys"
echo "   2. Configure Nginx reverse proxy (see VPS_DEPLOYMENT_GUIDE.md)"
echo "   3. Set up SSL certificate with certbot"
echo "   4. Update DNS to point to this server"
echo ""
print_warning "Remember to:"
echo "   - Change all default passwords in .env"
echo "   - Set up nginx reverse proxy"
echo "   - Configure SSL/HTTPS"
echo "   - Set up regular backups"
echo ""
print_success "Happy deploying! 🚀"

