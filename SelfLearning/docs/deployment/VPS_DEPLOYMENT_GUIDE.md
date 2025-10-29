# VPS Deployment Guide

**Complete guide to deploy your Blog Q&A system to a production VPS**

## Prerequisites

What you need:
- ✅ VPS IP address
- ✅ SSH credentials (username/password or SSH key)
- ✅ Root or sudo access
- ✅ Domain name (optional, but recommended)

---

## Step 1: Connect to Your VPS

### Using Password Authentication
```bash
ssh username@YOUR_VPS_IP
# Enter password when prompted
```

### Using SSH Key (More Secure)
```bash
ssh -i /path/to/your/key.pem username@YOUR_VPS_IP
```

Common usernames: `root`, `ubuntu`, `admin`, `centos`

### Test Connection
```bash
# Once connected, verify you're on the VPS
hostname
whoami
```

---

## Step 2: Update System

### For Ubuntu/Debian
```bash
sudo apt update
sudo apt upgrade -y
```

### For CentOS/RHEL
```bash
sudo yum update -y
```

---

## Step 3: Install Docker & Docker Compose

### Option A: Automatic Installation (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# IMPORTANT: Log out and back in for group changes to take effect
exit
```

### Option B: Manual Installation (Ubuntu 20.04/22.04)
```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

---

## Step 4: Install Additional Tools

```bash
# Install git (if not already installed)
sudo apt install -y git

# Install jq (for JSON parsing)
sudo apt install -y jq

# Install nginx (optional, for reverse proxy)
sudo apt install -y nginx

# Install certbot (for SSL certificates)
sudo apt install -y certbot python3-certbot-nginx
```

---

## Step 5: Transfer Your Application

### Option A: Using Git (Recommended)
```bash
# On VPS
cd /home/$USER
git clone YOUR_REPOSITORY_URL SelfLearning
cd SelfLearning
```

### Option B: Using SCP (From Your Local Machine)
```bash
# From your local machine
cd /Users/aks000z/Documents/personal_repo
tar -czf selflearning.tar.gz SelfLearning/
scp selflearning.tar.gz username@YOUR_VPS_IP:/home/username/

# Then on VPS
ssh username@YOUR_VPS_IP
cd /home/$USER
tar -xzf selflearning.tar.gz
cd SelfLearning
```

### Option C: Using rsync (From Your Local Machine)
```bash
# From your local machine - syncs entire directory
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
  /Users/aks000z/Documents/personal_repo/SelfLearning/ \
  username@YOUR_VPS_IP:/home/username/SelfLearning/
```

---

## Step 6: Configure Environment Variables

### Create Production Environment File
```bash
cd /home/$USER/SelfLearning

# Create .env file with production settings
cat > .env << 'EOF'
# ============================================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# ============================================================================

# MongoDB Configuration
MONGODB_URL=mongodb://mongodb:27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=CHANGE_THIS_SECURE_PASSWORD_123
DATABASE_NAME=blog_qa_db

# PostgreSQL Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=blog_qa_publishers
POSTGRES_USER=admin
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD_456

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_OPENAI_API_KEY_HERE
OPENAI_MODEL=gpt-4o-mini

# API Service Configuration
API_SERVICE_PORT=8005
ADMIN_API_KEY=CHANGE_THIS_TO_SECURE_ADMIN_KEY_789

# Worker Service Configuration
WORKER_POLL_INTERVAL=10

# CORS Configuration (set your actual domains)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Logging
LOG_LEVEL=INFO
EOF

# Secure the .env file
chmod 600 .env

echo "⚠️  IMPORTANT: Edit .env and change all passwords and API keys!"
```

### Edit the Environment File
```bash
nano .env
# or
vi .env
```

**Change these values:**
- `MONGODB_PASSWORD` - Strong password for MongoDB
- `POSTGRES_PASSWORD` - Strong password for PostgreSQL
- `OPENAI_API_KEY` - Your actual OpenAI API key
- `ADMIN_API_KEY` - Secure admin key for API access
- `CORS_ORIGINS` - Your actual domain(s)

---

## Step 7: Update Docker Compose for Production

### Create Production Docker Compose File
```bash
cd /home/$USER/SelfLearning

cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  # MongoDB
  mongodb:
    image: mongo:7.0
    container_name: blog-qa-mongodb-prod
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGODB_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD}
      MONGO_INITDB_DATABASE: ${DATABASE_NAME}
    volumes:
      - mongodb_data:/data/db
    networks:
      - blog-qa-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    container_name: blog-qa-postgres-prod
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - blog-qa-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # API Service
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
      - blog-qa-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Worker Service
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
      - blog-qa-network

networks:
  blog-qa-network:
    driver: bridge

volumes:
  mongodb_data:
  postgres_data:
EOF
```

---

## Step 8: Deploy the Application

### Build and Start Services
```bash
cd /home/$USER/SelfLearning

# Build images
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### Verify Services are Running
```bash
# Check all containers
docker ps

# Check API health
curl http://localhost:8005/health

# Check API docs
curl http://localhost:8005/docs
```

---

## Step 9: Configure Firewall

### Using UFW (Ubuntu)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if accessing directly)
sudo ufw allow 8005/tcp

# Check status
sudo ufw status
```

### Using firewalld (CentOS/RHEL)
```bash
# Start firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Allow services
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8005/tcp

# Reload
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-all
```

---

## Step 10: Set Up Nginx Reverse Proxy (Recommended)

### Install and Configure Nginx
```bash
sudo apt install -y nginx

# Create nginx configuration
sudo nano /etc/nginx/sites-available/fyi-widget-api
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8005/health;
        access_log off;
    }
}
```

### Enable the Site
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/fyi-widget-api /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Step 11: Set Up SSL Certificate (HTTPS)

### Using Let's Encrypt (Free)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certbot will automatically:
# 1. Obtain the certificate
# 2. Update nginx configuration
# 3. Reload nginx

# Test auto-renewal
sudo certbot renew --dry-run
```

**Your API will now be accessible via:**
- `https://yourdomain.com`
- `https://yourdomain.com/docs` (API documentation)

---

## Step 12: Set Up Auto-Start on Reboot

### Create Systemd Service (Optional)
```bash
sudo nano /etc/systemd/system/blog-qa.service
```

**Service Configuration:**
```ini
[Unit]
Description=Blog Q&A Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/SelfLearning
ExecStart=/usr/local/bin/docker-compose -f docker-compose.production.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.production.yml down
User=YOUR_USERNAME

[Install]
WantedBy=multi-user.target
```

```bash
# Enable service
sudo systemctl enable blog-qa.service

# Start service
sudo systemctl start blog-qa.service

# Check status
sudo systemctl status blog-qa.service
```

---

## Step 13: Monitoring and Maintenance

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f api-service
docker-compose -f docker-compose.production.yml logs -f worker-service

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail 100 worker-service
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.production.yml restart

# Restart specific service
docker-compose -f docker-compose.production.yml restart api-service
docker-compose -f docker-compose.production.yml restart worker-service
```

### Update Application
```bash
cd /home/$USER/SelfLearning

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps
```

### Backup Databases
```bash
# Create backup directory
mkdir -p ~/backups

# Backup MongoDB
docker exec blog-qa-mongodb-prod mongodump \
  --username admin \
  --password YOUR_MONGODB_PASSWORD \
  --authenticationDatabase admin \
  --out /backup
docker cp blog-qa-mongodb-prod:/backup ~/backups/mongodb-$(date +%Y%m%d)

# Backup PostgreSQL
docker exec blog-qa-postgres-prod pg_dump \
  -U admin blog_qa_publishers > ~/backups/postgres-$(date +%Y%m%d).sql
```

---

## Quick Reference Commands

```bash
# Start services
docker-compose -f docker-compose.production.yml up -d

# Stop services
docker-compose -f docker-compose.production.yml down

# View logs (continuous)
docker logs -f fyi-widget-worker-service-prod

# Check API health
curl http://localhost:8005/health

# Check container status
docker ps

# Restart specific container
docker restart fyi-widget-api-prod

# View resource usage
docker stats

# Clean up unused images/containers
docker system prune -a
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Check individual container
docker logs fyi-widget-api-prod

# Check if ports are available
sudo netstat -tulpn | grep 8005
```

### Can't Connect to API
```bash
# Check if container is running
docker ps | grep api

# Check firewall
sudo ufw status

# Test locally
curl http://localhost:8005/health

# Check nginx
sudo nginx -t
sudo systemctl status nginx
```

### Database Connection Issues
```bash
# Check MongoDB
docker exec -it blog-qa-mongodb-prod mongosh -u admin -p

# Check PostgreSQL
docker exec -it blog-qa-postgres-prod psql -U admin -d blog_qa_publishers
```

### Out of Disk Space
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Check large files
du -sh /var/lib/docker/*
```

---

## Security Best Practices

✅ **Change all default passwords**
✅ **Use strong admin API keys**
✅ **Enable firewall (UFW)**
✅ **Set up SSL/HTTPS**
✅ **Keep system updated**: `sudo apt update && sudo apt upgrade`
✅ **Use SSH keys instead of passwords**
✅ **Disable root SSH login** (in `/etc/ssh/sshd_config`)
✅ **Set up fail2ban**: `sudo apt install fail2ban`
✅ **Regular backups**
✅ **Monitor logs regularly**
✅ **Use environment variables for secrets** (never commit to git)

---

## Production Checklist

- [ ] VPS is updated and secured
- [ ] Docker and Docker Compose installed
- [ ] Application code deployed
- [ ] Environment variables configured
- [ ] All passwords changed from defaults
- [ ] Services are running
- [ ] Firewall is configured
- [ ] Nginx reverse proxy set up
- [ ] SSL certificate installed
- [ ] Domain DNS configured
- [ ] API is accessible via HTTPS
- [ ] Logs are being written
- [ ] Backup strategy in place
- [ ] Auto-restart on reboot configured

---

**Your application is now deployed and running in production! 🚀**

For support: Check logs and monitor the services regularly.

