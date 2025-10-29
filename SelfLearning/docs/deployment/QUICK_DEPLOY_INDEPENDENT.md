# Quick Start: Independent Service Deployment

## 🎯 What This Does

Break down your services into **independent deployments** so you can:
- Deploy MongoDB, PostgreSQL, API, and Worker **separately**
- Update one service without affecting others
- Scale services independently
- Test each service on VPS separately

## 📁 Files Created

```
docker-compose.mongodb.yml     # MongoDB standalone
docker-compose.postgres.yml    # PostgreSQL standalone
docker-compose.api.yml         # API service standalone
docker-compose.worker.yml      # Worker service standalone

scripts/
  deploy-databases.sh         # Deploy MongoDB + PostgreSQL
  deploy-api.sh               # Deploy API service
  deploy-worker.sh            # Deploy Worker service
```

## 🚀 Quick Start

### Step 1: Deploy Databases

```bash
cd /path/to/SelfLearning

# Deploy both databases
./scripts/deploy-databases.sh

# Or individually:
docker-compose -f docker-compose.mongodb.yml up -d
docker-compose -f docker-compose.postgres.yml up -d
```

### Step 2: Deploy API

```bash
./scripts/deploy-api.sh

# Or manually:
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml up -d
```

### Step 3: Deploy Worker

```bash
./scripts/deploy-worker.sh

# Or manually:
docker-compose -f docker-compose.worker.yml build
docker-compose -f docker-compose.worker.yml up -d
```

## ✅ Verify Everything

```bash
# Check all services
docker ps | grep blog-qa

# Should show:
# blog-qa-mongodb
# blog-qa-postgres
# fyi-widget-api
# fyi-widget-worker-service

# Test API
curl http://localhost:8005/health

# View logs
docker logs -f fyi-widget-api
docker logs -f fyi-widget-worker-service
```

## 🔄 Update Individual Services

```bash
# Update API only (databases keep running)
cd /path/to/SelfLearning
git pull
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml up -d

# Update Worker only
docker-compose -f docker-compose.worker.yml build
docker-compose -f docker-compose.worker.yml up -d

# Databases stay running - zero downtime!
```

## 🌐 Deploy to VPS (Step by Step)

### On Your VPS:

```bash
# 1. SSH to VPS
ssh user@your-vps-ip

# 2. Clone/transfer your project
cd ~
git clone YOUR_REPO project-x
cd project-x/SelfLearning

# 3. Create .env
cp env.production.example .env
nano .env  # Fill in passwords/keys
chmod 600 .env

# 4. Deploy databases first
./scripts/deploy-databases.sh

# 5. Verify databases
docker ps | grep -E "mongodb|postgres"

# 6. Deploy API
./scripts/deploy-api.sh

# 7. Verify API
curl http://localhost:8005/health

# 8. Deploy Worker
./scripts/deploy-worker.sh

# 9. Verify Worker
docker logs fyi-widget-worker-service --tail 20
```

## 📊 Benefits

✅ **Independent Updates**: Update API without touching databases
✅ **Zero Downtime**: Restart services independently
✅ **Easy Scaling**: Scale workers without affecting API
✅ **Better Testing**: Test each service on VPS separately
✅ **Fault Isolation**: One service crash doesn't affect others

## 🔧 Troubleshooting

### Service Can't Connect

```bash
# Check network
docker network ls | grep blog-qa-network

# Check database connectivity
docker exec fyi-widget-api ping -c 2 mongodb
docker exec fyi-widget-api ping -c 2 postgres

# Verify connection strings in .env
cat .env | grep -E "MONGODB_URL|POSTGRES_URL"
```

### Restart Specific Service

```bash
# Restart API only
docker-compose -f docker-compose.api.yml restart

# Restart Worker only
docker-compose -f docker-compose.worker.yml restart

# Databases keep running!
```

## 📝 Next Steps

1. ✅ Deploy databases on VPS
2. ✅ Deploy API on VPS
3. ✅ Deploy Worker on VPS
4. ✅ Setup Nginx reverse proxy
5. ✅ Configure SSL/HTTPS
6. ✅ Setup monitoring

See `DEPLOY_INDEPENDENT_SERVICES.md` for full documentation.


