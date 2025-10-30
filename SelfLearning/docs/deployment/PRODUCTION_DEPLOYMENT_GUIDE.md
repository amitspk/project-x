# Production Deployment Guide

**Complete guide for deploying your Blog Q&A system to production on a VPS**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [VPS Setup](#vps-setup)
4. [Application Deployment](#application-deployment)
5. [Nginx & SSL Configuration](#nginx--ssl-configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Backup Strategy](#backup-strategy)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required:
- ✅ VPS with Ubuntu 20.04/22.04 or similar Linux distribution
- ✅ Minimum 4GB RAM, 2 CPU cores, 50GB disk space (8GB RAM recommended)
- ✅ Root or sudo access
- ✅ Domain name (for SSL/HTTPS)
- ✅ SSH key or password authentication

### Optional but Recommended:
- ✅ DNS configured to point to your VPS
- ✅ Email configured for SSL certificate renewal notifications

---

## Pre-Deployment Checklist

### Local Machine Preparation

1. **Generate Secure Passwords & Keys**
   ```bash
   # MongoDB Password
   python3 -c "import secrets; print('MONGODB_PASSWORD=' + secrets.token_urlsafe(32))"
   
   # PostgreSQL Password
   python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
   
   # Admin API Key
   python3 -c "import secrets; print('ADMIN_API_KEY=admin_' + secrets.token_urlsafe(32))"
   ```

2. **Prepare Deployment Files**
   ```bash
   cd /path/to/project-x/SelfLearning
   
   # Ensure you have the production files
   ls -la docker-compose.production.yml
   ls -la .env.production.template
   ```

3. **Test Locally (Optional)**
   ```bash
   # Build and test production compose
   docker-compose -f docker-compose.production.yml build
   docker-compose -f docker-compose.production.yml config  # Validate config
   ```

---

## VPS Setup

### Step 1: Connect to VPS

```bash
ssh username@YOUR_VPS_IP
# or with key
ssh -i /path/to/key.pem username@YOUR_VPS_IP
```

### Step 2: Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban unattended-upgrades
```

### Step 3: Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes
exit
```

### Step 4: Configure Firewall

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (CRITICAL - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status verbose
```

### Step 5: Setup Fail2Ban (Security)

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status
```

### Step 6: Setup Automatic Security Updates

```bash
sudo dpkg-reconfigure -plow unattended-upgrades
sudo systemctl enable unattended-upgrades
```

---

## Application Deployment

### Step 1: Transfer Application to VPS

**Option A: Using Git (Recommended)**
```bash
# On VPS
cd ~
git clone YOUR_REPOSITORY_URL project-x
cd project-x/SelfLearning
```

**Option B: Using rsync (From Local)**
```bash
# From your local machine
rsync -avz --exclude 'node_modules' \
           --exclude '__pycache__' \
           --exclude '.git' \
           --exclude '*.pyc' \
           /path/to/project-x/SelfLearning/ \
           username@YOUR_VPS_IP:~/project-x/SelfLearning/
```

### Step 2: Configure Environment Variables

```bash
cd ~/project-x/SelfLearning

# Copy template
cp .env.production.template .env

# Edit with your values
nano .env
```

**Critical values to set:**
- `MONGODB_PASSWORD` - Strong password (32+ chars)
- `POSTGRES_PASSWORD` - Strong password (32+ chars)
- `ADMIN_API_KEY` - Secure admin key
- `OPENAI_API_KEY` - Your actual OpenAI API key
- `CORS_ORIGINS` - Your domain(s), comma-separated

**Secure the file:**
```bash
chmod 600 .env
```

### Step 3: Build and Start Services

```bash
# Build images (this may take several minutes)
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### Step 4: Verify Deployment

```bash
# Check all containers are running
docker ps

# Test API locally
curl http://localhost:8005/health

# Check logs for errors
docker-compose -f docker-compose.production.yml logs api-service
docker-compose -f docker-compose.production.yml logs worker-service
```

---

## Nginx & SSL Configuration

### Step 1: Install Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Step 2: Configure Nginx

```bash
# Copy production config
sudo cp ~/project-x/SelfLearning/nginx/nginx.production.conf \
       /etc/nginx/sites-available/fyi-widget-api

# Copy proxy settings
sudo mkdir -p /etc/nginx/conf.d
sudo cp ~/project-x/SelfLearning/nginx/proxy_settings.conf \
       /etc/nginx/conf.d/proxy_settings.conf

# Edit and update domain name
sudo nano /etc/nginx/sites-available/fyi-widget-api
# Replace 'yourdomain.com' with your actual domain

# Enable site
sudo ln -s /etc/nginx/sites-available/fyi-widget-api /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default config

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 3: Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Setup auto-renewal cron (usually added automatically)
sudo systemctl enable certbot.timer
```

### Step 4: Verify HTTPS

```bash
# Test HTTPS endpoint
curl https://yourdomain.com/health

# Test in browser
# Visit: https://yourdomain.com/docs
```

---

## Security Hardening

### 1. Database Security

```bash
# Verify databases are NOT exposed to public internet
sudo netstat -tulpn | grep -E '27017|5432'
# Should show only localhost/127.0.0.1, not 0.0.0.0
```

### 2. Container Security

```bash
# Ensure no unnecessary ports are exposed
docker ps --format "table {{.Names}}\t{{.Ports}}"

# API should only be accessible via nginx (localhost:8005)
```

### 3. System Security

```bash
# Disable root SSH login (if applicable)
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd

# Setup SSH key authentication (recommended)
# From local machine:
ssh-copy-id username@YOUR_VPS_IP

# Enable SSH key only (disable password auth)
# Edit /etc/ssh/sshd_config:
# PasswordAuthentication no
# PubkeyAuthentication yes
```

### 4. Regular Updates

```bash
# Schedule regular updates
sudo apt update && sudo apt upgrade -y

# Update Docker images periodically
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d
```

---

## Monitoring & Maintenance

### Service Management

```bash
# View all services
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Restart a service
docker-compose -f docker-compose.production.yml restart api-service

# View resource usage
docker stats

# Check service health
curl http://localhost:8005/health
```

### Log Management

```bash
# View recent API logs
docker logs --tail 100 fyi-widget-api-prod

# View worker logs
docker logs --tail 100 fyi-widget-worker-service-prod

# Follow logs in real-time
docker logs -f fyi-widget-worker-service-prod
```

### System Monitoring

```bash
# Install monitoring tools (optional)
sudo apt install -y htop iotop

# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up Docker (remove unused resources)
docker system prune -a --volumes  # Use with caution!
```

### Auto-Start on Reboot

```bash
# Create systemd service
sudo nano /etc/systemd/system/blog-qa.service
```

```ini
[Unit]
Description=Blog Q&A Production Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/project-x/SelfLearning
ExecStart=/usr/local/bin/docker-compose -f docker-compose.production.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.production.yml down
User=YOUR_USERNAME

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable blog-qa.service
sudo systemctl start blog-qa.service
```

---

## Backup Strategy

### Automated Backups

**Setup daily backups:**

```bash
# Make backup script executable
chmod +x ~/project-x/SelfLearning/scripts/backup_databases.sh

# Add to crontab (runs daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /home/YOUR_USERNAME/project-x/SelfLearning/scripts/backup_databases.sh >> /home/YOUR_USERNAME/backup.log 2>&1
```

**Manual backup:**
```bash
cd ~/project-x/SelfLearning
export MONGODB_PASSWORD="your_mongo_password"
export POSTGRES_PASSWORD="your_postgres_password"
./scripts/backup_databases.sh
```

**Restore from backup:**
```bash
./scripts/restore_databases.sh mongodb-20240101_120000.tar.gz postgres-20240101_120000.sql.gz
```

### Backup to Remote Storage (Optional)

```bash
# Install rclone for cloud backups
curl https://rclone.org/install.sh | sudo bash

# Configure (example for AWS S3)
rclone config

# Add to backup script to sync to cloud
# rclone sync ~/backups remote:fyi-widget-backups
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Check individual service
docker logs fyi-widget-api-prod
docker logs fyi-widget-worker-service-prod

# Check if ports are in use
sudo netstat -tulpn | grep 8005

# Restart services
docker-compose -f docker-compose.production.yml restart
```

### Database Connection Issues

```bash
# Test MongoDB connection
docker exec -it fyi-widget-mongodb-prod mongosh -u admin -p

# Test PostgreSQL connection
docker exec -it fyi-widget-postgres-prod psql -U postgres -d blog_qa_publishers

# Check database logs
docker logs fyi-widget-mongodb-prod
docker logs fyi-widget-postgres-prod
```

### API Not Accessible

```bash
# Test locally
curl http://localhost:8005/health

# Check nginx
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/fyi-widget-api-error.log

# Check firewall
sudo ufw status
```

### Out of Disk Space

```bash
# Check disk usage
df -h
du -sh /var/lib/docker/*

# Clean Docker
docker system prune -f
docker volume prune -f

# Clean old backups
find ~/backups -mtime +30 -delete
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check service limits in docker-compose.production.yml
# Adjust resource limits if needed

# Monitor database performance
docker exec -it fyi-widget-mongodb-prod mongosh --eval "db.serverStatus()"
```

---

## Production Checklist

- [ ] VPS is updated and secured
- [ ] Firewall is configured (UFW)
- [ ] Fail2Ban is enabled
- [ ] Docker and Docker Compose installed
- [ ] Application code deployed
- [ ] Environment variables configured with secure passwords
- [ ] `.env` file secured (chmod 600)
- [ ] Services are running (`docker ps`)
- [ ] API is accessible locally (`curl localhost:8005/health`)
- [ ] Nginx reverse proxy configured
- [ ] SSL certificate installed (HTTPS working)
- [ ] Domain DNS configured and pointing to VPS
- [ ] API is accessible via HTTPS domain
- [ ] Backups are configured and tested
- [ ] Auto-start on reboot is configured
- [ ] Monitoring/logging is in place
- [ ] All default passwords changed
- [ ] SSH keys configured (password auth disabled)
- [ ] Regular update schedule configured

---

## Quick Reference Commands

```bash
# Service management
docker-compose -f docker-compose.production.yml up -d      # Start
docker-compose -f docker-compose.production.yml down       # Stop
docker-compose -f docker-compose.production.yml restart    # Restart
docker-compose -f docker-compose.production.yml ps         # Status
docker-compose -f docker-compose.production.yml logs -f    # Logs

# Individual containers
docker logs -f fyi-widget-api-prod
docker logs -f fyi-widget-worker-service-prod
docker restart fyi-widget-api-prod

# Health checks
curl http://localhost:8005/health
curl https://yourdomain.com/health

# Updates
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Backups
./scripts/backup_databases.sh
```

---

## Support & Maintenance

**Regular Tasks:**
- Weekly: Review logs for errors
- Weekly: Check disk space
- Monthly: Update system packages
- Monthly: Update Docker images
- Monthly: Test backup restoration
- Quarterly: Review and rotate API keys/passwords

**Emergency Contacts:**
- Check application logs first
- Review system logs: `journalctl -xe`
- Check nginx logs: `/var/log/nginx/`
- Review Docker logs: `docker-compose logs`

---

**Your production deployment is complete! 🚀**

For ongoing maintenance, refer to the [Monitoring & Maintenance](#monitoring--maintenance) section.

