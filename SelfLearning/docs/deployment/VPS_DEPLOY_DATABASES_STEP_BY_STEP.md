# Step-by-Step: Deploy Databases to VPS

## 🎯 Goal
Deploy MongoDB and PostgreSQL independently on your VPS - **without copying entire project**.

---

## Step 1: Create Deployment Package (Local Machine)

```bash
# On your local machine
cd /path/to/project-x/SelfLearning

# Create minimal deployment package
./create-deployment-package.sh

# This creates: deployment/ folder (~1-5MB)
```

**What gets created:**
- ✅ docker-compose.mongodb.yml
- ✅ docker-compose.postgres.yml  
- ✅ Deployment scripts
- ✅ Environment templates
- ❌ NO source code
- ❌ NO large files

---

## Step 2: Transfer to VPS

```bash
# Option A: Transfer folder
scp -r deployment/ username@your-vps-ip:~/blog-qa

# Option B: Transfer tarball (smaller)
scp deployment.tar.gz username@your-vps-ip:~/
```

**Size:** Only 1-5MB (vs 500MB+ full project!)

---

## Step 3: Setup on VPS

### Connect to VPS

```bash
ssh username@your-vps-ip
```

### Extract (if using tarball)

```bash
cd ~
tar -xzf deployment.tar.gz
cd deployment
```

### Install Docker (If Not Already Installed)

```bash
# Check if Docker is installed
docker --version

# If not installed:
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
# SSH back in
```

---

## Step 4: Configure Environment

```bash
# Still on VPS
cd ~/blog-qa  # or ~/deployment if using tarball

# Copy environment template
cp env.production.example .env

# Generate secure passwords
python3 -c "import secrets; print('MONGODB_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"

# Edit .env file
nano .env
```

**In .env file, set:**
```bash
# MongoDB
MONGODB_USERNAME=admin
MONGODB_PASSWORD=<paste-generated-password>
DATABASE_NAME=blog_qa_db

# PostgreSQL  
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<paste-generated-password>
POSTGRES_DB=blog_qa_publishers
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

**Secure the file:**
```bash
chmod 600 .env
```

---

## Step 5: Deploy Databases

### Option A: Using Script (Easiest)

```bash
# Make script executable
chmod +x scripts/deploy-databases.sh

# Deploy both databases
./scripts/deploy-databases.sh
```

### Option B: Manual Deployment

```bash
# Create Docker network
docker network create blog-qa-network

# Deploy MongoDB
docker-compose -f docker-compose.mongodb.yml up -d

# Wait 10 seconds
sleep 10

# Deploy PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# Wait 10 seconds
sleep 10
```

---

## Step 6: Verify Deployment

```bash
# Check both databases are running
docker ps | grep -E "mongodb|postgres"

# Should show:
# blog-qa-mongodb    Up X minutes
# blog-qa-postgres   Up X minutes

# Test MongoDB
docker exec blog-qa-mongodb mongosh --eval "db.runCommand('ping')" --quiet

# Test PostgreSQL
docker exec blog-qa-postgres pg_isready -U postgres

# Check logs for errors
docker logs blog-qa-mongodb --tail 20
docker logs blog-qa-postgres --tail 20
```

**Expected output:**
```
✅ MongoDB connection: OK
✅ PostgreSQL connection: OK
```

---

## Step 7: Security - Configure Firewall

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (for API later)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# DO NOT expose database ports (27017, 5432) - they're localhost only!

# Check status
sudo ufw status
```

**Note:** Database ports are already secured - bound to `127.0.0.1` only in docker-compose files.

---

## Step 8: Setup Auto-Start (Optional)

```bash
# Create systemd service
sudo nano /etc/systemd/system/blog-qa-databases.service
```

**Paste this (replace YOUR_USERNAME):**
```ini
[Unit]
Description=Blog Q&A Databases
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/blog-qa
ExecStart=/usr/local/bin/docker-compose -f docker-compose.mongodb.yml -f docker-compose.postgres.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.mongodb.yml -f docker-compose.postgres.yml down
User=YOUR_USERNAME

[Install]
WantedBy=multi-user.target
```

**Enable service:**
```bash
# Replace YOUR_USERNAME with your actual username
sudo systemctl daemon-reload
sudo systemctl enable blog-qa-databases.service
sudo systemctl start blog-qa-databases.service

# Check status
sudo systemctl status blog-qa-databases.service
```

---

## Step 9: Setup Backups (Recommended)

```bash
# Make backup script executable
chmod +x scripts/backup_databases.sh

# Test backup
./scripts/backup_databases.sh

# Setup automated daily backups (runs at 2 AM)
crontab -e

# Add this line:
0 2 * * * cd /home/$USER/blog-qa && ./scripts/backup_databases.sh >> ~/backup.log 2>&1
```

---

## ✅ Success Checklist

- [ ] Docker and Docker Compose installed
- [ ] Deployment package transferred to VPS
- [ ] .env file configured with secure passwords
- [ ] MongoDB container running
- [ ] PostgreSQL container running
- [ ] Both databases respond to ping/health checks
- [ ] Firewall configured
- [ ] Auto-start configured (optional)
- [ ] Backups configured (optional)

---

## 🐛 Troubleshooting

### Databases Won't Start

```bash
# Check logs
docker logs blog-qa-mongodb --tail 50
docker logs blog-qa-postgres --tail 50

# Check if ports are in use
sudo netstat -tulpn | grep -E "27017|5432"

# Check disk space
df -h
```

### Can't Connect

```bash
# Verify containers are running
docker ps | grep -E "mongodb|postgres"

# Check network
docker network ls | grep blog-qa-network

# Test connectivity
docker exec blog-qa-mongodb ping -c 2 postgres
```

### Password Issues

```bash
# Verify .env file has correct passwords
cat .env | grep -E "MONGODB_PASSWORD|POSTGRES_PASSWORD"

# Restart containers with new passwords
docker-compose -f docker-compose.mongodb.yml restart
docker-compose -f docker-compose.postgres.yml restart
```

---

## 📊 Connection Info for Next Steps

After databases are deployed, you'll use these connection strings for API/Worker:

```bash
# MongoDB
mongodb://admin:YOUR_PASSWORD@mongodb:27017/blog_qa_db?authSource=admin

# PostgreSQL
postgresql+psycopg://postgres:YOUR_PASSWORD@postgres:5432/blog_qa_publishers
```

These will be used when you deploy API and Worker services next.

---

## 🚀 Next Steps

Once databases are running:

1. ✅ Verify both are healthy
2. ✅ Setup backups
3. ✅ **Deploy API service** (next step)
4. ✅ **Deploy Worker service** (after API)

---

## Quick Commands Reference

```bash
# Check status
docker ps | grep -E "mongodb|postgres"

# View logs
docker logs -f blog-qa-mongodb
docker logs -f blog-qa-postgres

# Restart
docker-compose -f docker-compose.mongodb.yml restart
docker-compose -f docker-compose.postgres.yml restart

# Stop
docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.postgres.yml down
```

---

**Your databases are now deployed! 🎉**

Proceed to deploy API and Worker services next.


