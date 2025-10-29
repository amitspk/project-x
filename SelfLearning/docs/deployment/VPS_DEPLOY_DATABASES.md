# Deploying Databases on VPS

Complete guide for deploying MongoDB and PostgreSQL independently on your VPS.

---

## Prerequisites

- ✅ VPS with Ubuntu 20.04/22.04 or similar
- ✅ Docker and Docker Compose installed
- ✅ SSH access to VPS
- ✅ Root or sudo access

---

## Step-by-Step Deployment

### Step 1: Connect to VPS

```bash
ssh username@your-vps-ip
```

### Step 2: Install Docker (If Not Already Installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version

# Log out and back in for group changes
exit
# Then SSH back in
```

### Step 3: Transfer Project Files to VPS

**Option A: Using Git (Recommended)**

```bash
# On VPS
cd ~
git clone YOUR_REPOSITORY_URL project-x
cd project-x/SelfLearning
```

**Option B: Using rsync (From Local Machine)**

```bash
# From your local machine
rsync -avz --exclude 'node_modules' \
           --exclude '__pycache__' \
           --exclude '.git' \
           --exclude '*.pyc' \
           /path/to/SelfLearning/ \
           username@your-vps-ip:~/project-x/SelfLearning/
```

### Step 4: Configure Environment Variables

```bash
cd ~/project-x/SelfLearning

# Copy environment template
cp env.production.example .env

# Edit with your secure passwords
nano .env
```

**Set these values in `.env`:**

```bash
# MongoDB Configuration
MONGODB_USERNAME=admin
MONGODB_PASSWORD=CHANGE_THIS_GENERATE_SECURE_PASSWORD_32_CHARS_MIN
DATABASE_NAME=blog_qa_db

# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGE_THIS_GENERATE_SECURE_PASSWORD_32_CHARS_MIN
POSTGRES_DB=blog_qa_publishers
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Generate secure passwords (run on VPS):
# MongoDB Password:
python3 -c "import secrets; print('MONGODB_PASSWORD=' + secrets.token_urlsafe(32))"

# PostgreSQL Password:
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
```

**Secure the file:**
```bash
chmod 600 .env
```

### Step 5: Deploy Databases

**Option A: Using Deployment Script (Easiest)**

```bash
# Make script executable
chmod +x scripts/deploy-databases.sh

# Run deployment
./scripts/deploy-databases.sh
```

**Option B: Manual Deployment**

```bash
# Create Docker network
docker network create blog-qa-network

# Deploy MongoDB
docker-compose -f docker-compose.mongodb.yml up -d

# Wait for MongoDB to be healthy
sleep 10

# Deploy PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# Wait for PostgreSQL to be healthy
sleep 10

# Verify both are running
docker ps | grep -E "mongodb|postgres"
```

### Step 6: Verify Deployment

```bash
# Check container status
docker ps | grep -E "mongodb|postgres"

# Should show:
# blog-qa-mongodb    Up X minutes
# blog-qa-postgres   Up X minutes

# Test MongoDB connection
docker exec blog-qa-mongodb mongosh --eval "db.runCommand('ping')" --quiet

# Test PostgreSQL connection
docker exec blog-qa-postgres pg_isready -U postgres

# Check logs for errors
docker logs blog-qa-mongodb --tail 20
docker logs blog-qa-postgres --tail 20
```

---

## Security Configuration

### Firewall Setup

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (for API later)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# DO NOT expose database ports externally!
# MongoDB (27017) and PostgreSQL (5432) should only be accessible locally

# Check status
sudo ufw status
```

**Important**: Database ports (27017, 5432) are bound to `127.0.0.1` only, so they're not exposed to the internet. Only accessible from:
- Localhost on VPS
- Docker containers on same network

---

## Verify Database Access

### MongoDB

```bash
# Connect via docker exec
docker exec -it blog-qa-mongodb mongosh -u admin -p

# Or test connection
docker exec blog-qa-mongodb mongosh --eval "db.runCommand({connectionStatus: 1})" --quiet
```

### PostgreSQL

```bash
# Connect via docker exec
docker exec -it blog-qa-postgres psql -U postgres -d blog_qa_publishers

# Or test connection
docker exec blog-qa-postgres pg_isready -U postgres
```

---

## Backup Setup

### Manual Backup

```bash
# Make backup script executable
chmod +x scripts/backup_databases.sh

# Run backup
./scripts/backup_databases.sh
```

### Automated Daily Backups

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * cd /home/$USER/project-x/SelfLearning && ./scripts/backup_databases.sh >> ~/backup.log 2>&1
```

---

## Connecting from Application Services

Once databases are deployed, your API and Worker services can connect using:

### Local Docker Network (Same VPS)

In your `.env` file for API/Worker:

```bash
# MongoDB - using container hostname
MONGODB_URL=mongodb://admin:your-password@mongodb:27017/blog_qa_db?authSource=admin

# PostgreSQL - using container hostname
POSTGRES_URL=postgresql+psycopg://postgres:your-password@postgres:5432/blog_qa_publishers
POSTGRES_HOST=postgres
```

### External Connection (Different VPS)

If your databases are on VPS1 and apps on VPS2:

```bash
# On VPS2, update .env with VPS1 IP:
MONGODB_URL=mongodb://admin:password@VPS1_IP:27017/blog_qa_db?authSource=admin
POSTGRES_URL=postgresql+psycopg://postgres:password@VPS1_IP:5432/blog_qa_publishers
POSTGRES_HOST=VPS1_IP

# On VPS1, expose ports (carefully, with firewall rules):
# Edit docker-compose.mongodb.yml to bind to 0.0.0.0:27017 (not recommended)
# Better: Use SSH tunnel or VPN
```

---

## Service Management

### Check Status

```bash
# All database containers
docker ps | grep -E "mongodb|postgres"

# Specific container
docker ps | grep mongodb
docker ps | grep postgres
```

### View Logs

```bash
# MongoDB logs
docker logs -f blog-qa-mongodb

# PostgreSQL logs
docker logs -f blog-qa-postgres

# Last 50 lines
docker logs blog-qa-mongodb --tail 50
```

### Restart Services

```bash
# Restart MongoDB
docker-compose -f docker-compose.mongodb.yml restart

# Restart PostgreSQL
docker-compose -f docker-compose.postgres.yml restart

# Or using docker directly
docker restart blog-qa-mongodb
docker restart blog-qa-postgres
```

### Stop Services

```bash
# Stop MongoDB
docker-compose -f docker-compose.mongodb.yml down

# Stop PostgreSQL
docker-compose -f docker-compose.postgres.yml down

# Stop both
docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.postgres.yml down
```

### Update Service Configuration

```bash
# Edit docker-compose file
nano docker-compose.mongodb.yml

# Apply changes
docker-compose -f docker-compose.mongodb.yml up -d
```

---

## Auto-Start on Reboot

Create systemd service to ensure databases start automatically:

```bash
sudo nano /etc/systemd/system/blog-qa-databases.service
```

Add this content:

```ini
[Unit]
Description=Blog Q&A Databases
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/project-x/SelfLearning
ExecStart=/usr/local/bin/docker-compose -f docker-compose.mongodb.yml -f docker-compose.postgres.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.mongodb.yml -f docker-compose.postgres.yml down
User=YOUR_USERNAME

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
# Replace YOUR_USERNAME with your actual username
sudo systemctl daemon-reload
sudo systemctl enable blog-qa-databases.service
sudo systemctl start blog-qa-databases.service

# Check status
sudo systemctl status blog-qa-databases.service
```

---

## Troubleshooting

### Databases Won't Start

```bash
# Check logs
docker logs blog-qa-mongodb --tail 50
docker logs blog-qa-postgres --tail 50

# Check if ports are in use
sudo netstat -tulpn | grep -E "27017|5432"

# Check disk space
df -h

# Check Docker resources
docker stats --no-stream
```

### Can't Connect to Databases

```bash
# Verify containers are running
docker ps | grep -E "mongodb|postgres"

# Check network
docker network ls | grep blog-qa-network

# Test network connectivity
docker exec blog-qa-mongodb ping -c 2 postgres
docker exec blog-qa-postgres ping -c 2 mongodb

# Verify connection strings
cat .env | grep -E "MONGODB|POSTGRES"
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up unused images
docker system prune -f

# Check volume sizes
docker volume ls
docker volume inspect selflearning_mongodb_data
```

---

## Production Checklist

Before deploying API/Worker services:

- [ ] MongoDB is running and healthy
- [ ] PostgreSQL is running and healthy
- [ ] Database passwords are secure (32+ characters)
- [ ] `.env` file is secured (chmod 600)
- [ ] Firewall is configured (databases not exposed externally)
- [ ] Backups are configured and tested
- [ ] Auto-start on reboot is configured
- [ ] Logs are accessible and monitored
- [ ] Disk space is adequate (check regularly)
- [ ] Network connectivity verified between containers

---

## Quick Reference

```bash
# Deploy databases
./scripts/deploy-databases.sh

# Check status
docker ps | grep -E "mongodb|postgres"

# View logs
docker logs -f blog-qa-mongodb
docker logs -f blog-qa-postgres

# Test connections
docker exec blog-qa-mongodb mongosh --eval "db.runCommand('ping')"
docker exec blog-qa-postgres pg_isready -U postgres

# Backup
./scripts/backup_databases.sh

# Restart
docker-compose -f docker-compose.mongodb.yml restart
docker-compose -f docker-compose.postgres.yml restart
```

---

## Next Steps

After databases are deployed:

1. ✅ Verify both databases are running
2. ✅ Test connections manually
3. ✅ Setup automated backups
4. ✅ Deploy API service: `./scripts/deploy-api.sh`
5. ✅ Deploy Worker service: `./scripts/deploy-worker.sh`

---

**Your databases are now ready for production! 🚀**


