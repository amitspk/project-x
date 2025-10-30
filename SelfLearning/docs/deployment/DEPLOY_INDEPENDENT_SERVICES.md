# Independent Service Deployment Guide

This guide shows how to deploy MongoDB, PostgreSQL, API, and Worker services **independently** on your VPS.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   MongoDB       │     │  PostgreSQL     │
│   (Port 27017)  │     │  (Port 5432)    │
└─────────────────┘     └─────────────────┘
         │                      │
         └──────────┬──────────┘
                    │
    ┌───────────────┴───────────────┐
    │                                │
┌───▼────┐                     ┌───▼─────┐
│  API   │                     │ Worker  │
│ :8005  │                     │ (Back)  │
└────────┘                     └─────────┘
```

Each service can be:
- Deployed independently
- Updated without affecting others
- Scaled independently
- Managed separately

---

## File Structure

```
docker-compose.mongodb.yml     # MongoDB only
docker-compose.postgres.yml    # PostgreSQL only  
docker-compose.api.yml         # API service only
docker-compose.worker.yml      # Worker service only
```

---

## Deployment Steps

### Step 1: Deploy Databases First

#### Deploy MongoDB

```bash
cd /path/to/SelfLearning

# Create network (first time only)
docker network create fyi-widget-network || true

# Start MongoDB
docker-compose -f docker-compose.mongodb.yml up -d

# Verify
docker ps | grep mongodb
curl http://localhost:27017  # Should get connection error (normal)
```

#### Deploy PostgreSQL

```bash
# Start PostgreSQL (uses same network)
docker-compose -f docker-compose.postgres.yml up -d

# Verify
docker ps | grep postgres
docker exec fyi-widget-postgres pg_isready -U postgres
```

### Step 2: Deploy Application Services

#### Deploy API Service

```bash
# Ensure databases are running first
docker ps | grep -E "mongodb|postgres"

# Start API service
docker-compose -f docker-compose.api.yml up -d

# Verify
docker ps | grep api
curl http://localhost:8005/health
```

#### Deploy Worker Service

```bash
# Start worker service
docker-compose -f docker-compose.worker.yml up -d

# Verify
docker ps | grep worker
docker logs fyi-widget-worker-service --tail 20
```

---

## Configuration

### Environment Variables (.env)

```bash
# MongoDB
MONGODB_USERNAME=admin
MONGODB_PASSWORD=your-secure-password
DATABASE_NAME=blog_qa_db
MONGODB_URL=mongodb://admin:your-password@mongodb:27017/blog_qa_db?authSource=admin

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=blog_qa_publishers
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_URL=postgresql+psycopg://postgres:your-password@postgres:5432/blog_qa_publishers

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini

# API
ADMIN_API_KEY=your-admin-key
API_SERVICE_PORT=8005

# Worker
POLL_INTERVAL_SECONDS=5
CONCURRENT_JOBS=1
```

### External Database Support

If your databases are on **different VPS** or **managed services**:

```bash
# Update .env for external databases
MONGODB_URL=mongodb://admin:password@your-mongodb-host:27017/blog_qa_db
POSTGRES_URL=postgresql+psycopg://user:pass@your-postgres-host:5432/blog_qa_publishers
POSTGRES_HOST=your-postgres-host

# Remove depends_on from api/worker compose files
# They'll connect via network/hostname
```

---

## Quick Deployment Scripts

### deploy-databases.sh

```bash
#!/bin/bash
echo "🗄️  Deploying Databases..."

# Create network
docker network create fyi-widget-network 2>/dev/null || true

# Deploy MongoDB
echo "📦 Starting MongoDB..."
docker-compose -f docker-compose.mongodb.yml up -d

# Wait for MongoDB
echo "⏳ Waiting for MongoDB..."
sleep 10

# Deploy PostgreSQL
echo "📦 Starting PostgreSQL..."
docker-compose -f docker-compose.postgres.yml up -d

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
sleep 10

# Verify
echo "✅ Databases Status:"
docker ps | grep -E "mongodb|postgres"
```

### deploy-api.sh

```bash
#!/bin/bash
echo "🚀 Deploying API Service..."

# Check databases
if ! docker ps | grep -q mongodb; then
    echo "❌ MongoDB not running. Start it first:"
    echo "   docker-compose -f docker-compose.mongodb.yml up -d"
    exit 1
fi

if ! docker ps | grep -q postgres; then
    echo "❌ PostgreSQL not running. Start it first:"
    echo "   docker-compose -f docker-compose.postgres.yml up -d"
    exit 1
fi

# Build and start
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml up -d

echo "✅ API Service Status:"
docker ps | grep api
curl -s http://localhost:8005/health | head -5
```

### deploy-worker.sh

```bash
#!/bin/bash
echo "⚙️  Deploying Worker Service..."

# Check databases
if ! docker ps | grep -q mongodb; then
    echo "❌ MongoDB not running. Start it first."
    exit 1
fi

if ! docker ps | grep -q postgres; then
    echo "❌ PostgreSQL not running. Start it first."
    exit 1
fi

# Build and start
docker-compose -f docker-compose.worker.yml build
docker-compose -f docker-compose.worker.yml up -d

echo "✅ Worker Service Status:"
docker ps | grep worker
docker logs fyi-widget-worker-service --tail 10
```

---

## Service Management

### Check All Services

```bash
# All services
docker ps | grep blog-qa

# Specific service
docker ps | grep mongodb
docker ps | grep postgres
docker ps | grep api
docker ps | grep worker
```

### View Logs

```bash
# MongoDB
docker logs -f fyi-widget-mongodb

# PostgreSQL
docker logs -f fyi-widget-postgres

# API
docker logs -f fyi-widget-api

# Worker
docker logs -f fyi-widget-worker-service
```

### Restart Services

```bash
# Restart specific service
docker-compose -f docker-compose.mongodb.yml restart
docker-compose -f docker-compose.api.yml restart
docker-compose -f docker-compose.worker.yml restart
```

### Stop Services

```bash
# Stop API (databases keep running)
docker-compose -f docker-compose.api.yml down

# Stop Worker (databases keep running)
docker-compose -f docker-compose.worker.yml down

# Stop databases (careful - stops everything)
docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.postgres.yml down
```

### Update Services

```bash
# Update API only
cd /path/to/SelfLearning
git pull
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml up -d

# Update Worker only
docker-compose -f docker-compose.worker.yml build
docker-compose -f docker-compose.worker.yml up -d

# Databases stay running - no downtime!
```

---

## Scaling

### Scale Worker Service

```bash
# Run multiple worker instances
docker-compose -f docker-compose.worker.yml up -d --scale worker-service=3
```

### Separate VPS Deployment

Deploy services on different VPS servers:

**VPS 1 (Databases):**
```bash
# Deploy MongoDB and PostgreSQL
docker-compose -f docker-compose.mongodb.yml up -d
docker-compose -f docker-compose.postgres.yml up -d
```

**VPS 2 (API):**
```bash
# Update .env with VPS 1 IP
MONGODB_URL=mongodb://admin:pass@VPS1_IP:27017/blog_qa_db
POSTGRES_URL=postgresql+psycopg://user:pass@VPS1_IP:5432/blog_qa_publishers

docker-compose -f docker-compose.api.yml up -d
```

**VPS 3 (Workers):**
```bash
# Same configuration as VPS 2
docker-compose -f docker-compose.worker.yml up -d --scale worker-service=5
```

---

## Benefits of Independent Deployment

1. **Zero Downtime Updates**
   - Update API without restarting databases
   - Scale workers independently
   - Database maintenance doesn't affect API

2. **Resource Management**
   - Databases on dedicated VPS
   - API on high-CPU VPS
   - Workers on separate VPS

3. **Cost Optimization**
   - Use smaller VPS for databases
   - Scale workers based on load
   - Separate development/staging/production

4. **Fault Isolation**
   - Worker crash doesn't affect API
   - Database issue isolated from services
   - Better debugging and monitoring

---

## Troubleshooting

### Service Can't Connect to Database

```bash
# Check network
docker network ls | grep fyi-widget-network

# Check database is accessible
docker exec fyi-widget-api ping -c 2 mongodb
docker exec fyi-widget-api ping -c 2 postgres

# Check connection string in .env
cat .env | grep -E "MONGODB|POSTGRES"
```

### Port Conflicts

```bash
# Check if ports are in use
sudo netstat -tulpn | grep -E "27017|5432|8005"

# If needed, change ports in docker-compose files
```

### Service Health Checks

```bash
# API health
curl http://localhost:8005/health

# MongoDB
docker exec fyi-widget-mongodb mongosh --eval "db.runCommand('ping')"

# PostgreSQL
docker exec fyi-widget-postgres pg_isready -U postgres
```

---

## Production Checklist

- [ ] Databases deployed and running
- [ ] Network created (`fyi-widget-network`)
- [ ] Environment variables configured (.env)
- [ ] API service deployed and healthy
- [ ] Worker service deployed and processing jobs
- [ ] Backups configured for databases
- [ ] Monitoring set up for all services
- [ ] Firewall configured (ports accessible internally only)
- [ ] Nginx reverse proxy configured for API
- [ ] SSL certificates installed

---

## Quick Reference

```bash
# Start all services (in order)
./deploy-databases.sh
./deploy-api.sh
./deploy-worker.sh

# Or manually:
docker-compose -f docker-compose.mongodb.yml up -d
docker-compose -f docker-compose.postgres.yml up -d
docker-compose -f docker-compose.api.yml up -d
docker-compose -f docker-compose.worker.yml up -d

# Check status
docker ps | grep blog-qa

# View logs
docker logs -f fyi-widget-api

# Stop specific service
docker-compose -f docker-compose.api.yml down

# Update specific service
docker-compose -f docker-compose.api.yml build && docker-compose -f docker-compose.api.yml up -d
```


