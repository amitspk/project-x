# Docker Compose Commands Reference

Quick reference for common Docker Compose commands used in this project.

---

## 🔄 Restart Commands

### Zero-Downtime API Rolling Update

Use the helper script to pull the latest image and restart each API instance one at a time so that traffic always has at least one healthy target.

```bash
/home/amit/deployment/v7/scripts/rolling-update-api.sh
```

The script verifies the peer container is healthy before restarting the next one and waits for the health check to pass after each redeploy.

> **Note:** Run the script directly (e.g., `./scripts/rolling-update-api.sh`) so it executes with Bash; invoking it with `sh` will fail.

If one of the API containers is stopped or missing, the script will issue a warning and continue (zero-downtime cannot be guaranteed in that case).

### Restart All Services in a Compose File

```bash
# API Service
docker-compose -f docker-compose.api.yml restart

# Worker Service
docker-compose -f docker-compose.worker.yml restart

# Monitoring Stack
docker-compose -f docker-compose.monitoring.yml restart

# Databases
docker-compose -f docker-compose.databases.yml restart

# Database Admin UIs
docker-compose -f docker-compose.db-admins.yml restart
```

### Restart Specific Service

```bash
# Restart only API service
docker-compose -f docker-compose.api.yml restart api-service

# Restart only Worker service
docker-compose -f docker-compose.worker.yml restart worker-service

# Restart only Grafana
docker-compose -f docker-compose.monitoring.yml restart grafana

# Restart only Prometheus
docker-compose -f docker-compose.monitoring.yml restart prometheus

# Restart only Alertmanager
docker-compose -f docker-compose.monitoring.yml restart alertmanager

# Restart MongoDB
docker-compose -f docker-compose.databases.yml restart mongodb

# Restart PostgreSQL
docker-compose -f docker-compose.databases.yml restart postgres
```

### Restart Multiple Services

```bash
# Restart multiple services from same compose file
docker-compose -f docker-compose.monitoring.yml restart grafana prometheus alertmanager

# Restart all monitoring services
docker-compose -f docker-compose.monitoring.yml restart loki promtail prometheus alertmanager grafana
```

---

## 🚀 Start Services

> **Shared volumes:** The monitoring stack now mounts persistent Docker volumes with fixed names (`fyi-widget-grafana-data`, `fyi-widget-prometheus-data`, `fyi-widget-alertmanager-data`, `fyi-widget-loki-data`). Create them once via `docker volume create <name>` (or let the first compose run create them) and they will be reused across versioned folders (`v2`, `v3`, `v4`, ...).
>
> **Database volumes:** MongoDB and PostgreSQL also use shared volumes (`fyi-widget-mongodb-data`, `fyi-widget-mongodb-backup`, `fyi-widget-postgres-data`, `fyi-widget-postgres-backup`). These must exist (or be created once) before starting the database stack to preserve data between version folders.

### Start All Services in a Compose File

```bash
docker-compose -f docker-compose.api.yml up -d
docker-compose -f docker-compose.worker.yml up -d
docker-compose -f docker-compose.monitoring.yml up -d
docker-compose -f docker-compose.databases.yml up -d
```

### Start Specific Service

```bash
docker-compose -f docker-compose.api.yml up -d api-service
docker-compose -f docker-compose.monitoring.yml up -d grafana
```

---

## 🛑 Stop Services

### Stop All Services (Keeps Containers)

```bash
docker-compose -f docker-compose.api.yml stop
docker-compose -f docker-compose.worker.yml stop
docker-compose -f docker-compose.monitoring.yml stop
```

### Stop Specific Service

```bash
docker-compose -f docker-compose.api.yml stop api-service
docker-compose -f docker-compose.monitoring.yml stop grafana
```

### Stop and Remove Containers

```bash
# Stop and remove containers (keeps volumes)
docker-compose -f docker-compose.api.yml down

# Stop and remove containers + volumes (⚠️ DELETES DATA)
docker-compose -f docker-compose.api.yml down -v
```

---

## 🔍 View Status

### List Running Containers

```bash
# All containers
docker ps

# Filter by project
docker ps | grep fyi-widget

# All containers (including stopped)
docker ps -a
```

### View Service Logs

```bash
# Follow logs for all services
docker-compose -f docker-compose.api.yml logs -f

# Follow logs for specific service
docker-compose -f docker-compose.api.yml logs -f api-service

# Last 100 lines
docker-compose -f docker-compose.api.yml logs --tail 100 api-service

# Last 50 lines and follow
docker-compose -f docker-compose.monitoring.yml logs --tail 50 -f grafana
```

### View Service Status

```bash
# Show service status
docker-compose -f docker-compose.api.yml ps

# Show service status with details
docker-compose -f docker-compose.monitoring.yml ps -a
```

---

## 🔨 Rebuild and Restart

### Rebuild and Start (for build: configurations)

```bash
# Rebuild and start
docker-compose -f docker-compose.api.yml up -d --build

# Rebuild without cache
docker-compose -f docker-compose.api.yml build --no-cache
docker-compose -f docker-compose.api.yml up -d
```

---

## 📊 Resource Usage

### View Resource Usage

```bash
# Container stats
docker stats

# Filter by name
docker stats fyi-widget-api fyi-widget-worker-service
```

---

## 🗑️ Cleanup Commands

### Remove Stopped Containers

```bash
docker container prune
```

### Remove Unused Images

```bash
docker image prune
```

### Remove Unused Volumes (⚠️ CAREFUL)

```bash
docker volume prune
```

### Full Cleanup (⚠️ DANGEROUS - removes everything unused)

```bash
docker system prune -a
```

---

## 🔧 Common Workflows

### Restart After .env Changes

```bash
# 1. Update .env file
nano .env

# 2. Generate Alertmanager config (if changed monitoring settings)
./alertmanager/generate-alertmanager-config.sh

# 3. Restart affected services
docker-compose -f docker-compose.api.yml restart
docker-compose -f docker-compose.monitoring.yml restart alertmanager
```

### Restart After Config File Changes

```bash
# 1. Edit config file (e.g., prometheus.yml)
nano prometheus/prometheus.yml

# 2. Restart service
docker-compose -f docker-compose.monitoring.yml restart prometheus
```

### Restart All Services

```bash
# Restart all in order
docker-compose -f docker-compose.databases.yml restart
docker-compose -f docker-compose.monitoring.yml restart
docker-compose -f docker-compose.api.yml restart
docker-compose -f docker-compose.worker.yml restart
```

---

## 🚨 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.api.yml logs api-service

# Check container status
docker-compose -f docker-compose.api.yml ps

# Try starting without detached mode to see errors
docker-compose -f docker-compose.api.yml up api-service
```

### Force Restart (Stop + Remove + Start)

```bash
docker-compose -f docker-compose.api.yml down
docker-compose -f docker-compose.api.yml up -d
```

---

## 📝 Quick Reference Card

```bash
# Start
docker-compose -f FILE.yml up -d

# Stop
docker-compose -f FILE.yml stop

# Restart
docker-compose -f FILE.yml restart

# Restart specific
docker-compose -f FILE.yml restart SERVICE_NAME

# Logs
docker-compose -f FILE.yml logs -f SERVICE_NAME

# Status
docker-compose -f FILE.yml ps

# Down (remove)
docker-compose -f FILE.yml down

# Down + volumes (⚠️ deletes data)
docker-compose -f FILE.yml down -v
```

---

## 🎯 For This Project

### Typical Restart Sequence

```bash
# 1. Databases (foundation)
docker-compose -f docker-compose.databases.yml restart

# 2. Monitoring (needs databases for exporters)
docker-compose -f docker-compose.monitoring.yml restart

# 3. Application services
docker-compose -f docker-compose.api.yml restart
docker-compose -f docker-compose.worker.yml restart
```

### Restart Everything

```bash
cd /path/to/deployment/prod

docker-compose -f docker-compose.databases.yml restart
docker-compose -f docker-compose.monitoring.yml restart
docker-compose -f docker-compose.api.yml restart
docker-compose -f docker-compose.worker.yml restart
```

---

*Quick tip: Use `docker-compose` (with hyphen) for older versions, or `docker compose` (without hyphen) for newer Docker versions with Compose plugin.*

