# VPS Deployment Checklist

## ✅ Pre-Deployment Verification

### 1. Environment Files

- [ ] **Create `.env` file** in `deployment/prod/` directory
- [ ] **Use `env.production.example`** as base template
- [ ] **Generate secure passwords**:
  ```bash
  # MongoDB Password
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  
  # PostgreSQL Password
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  
  # Admin API Key
  python3 -c "import secrets; print('admin_' + secrets.token_urlsafe(32))"
  ```

- [ ] **Update all required variables**:
  - [ ] `OPENAI_API_KEY` - Your OpenAI API key
  - [ ] `ADMIN_API_KEY` - Generated secure admin key
  - [ ] `MONGODB_PASSWORD` - Generated secure password
  - [ ] `POSTGRES_PASSWORD` - Generated secure password
  - [ ] `CORS_ORIGINS` - Your production domain(s)

---

### 2. Monitoring Configuration

- [ ] **Update Grafana settings** in `.env`:
  - [ ] `GRAFANA_ADMIN_PASSWORD` - Change from default `admin`
  - [ ] `GRAFANA_SERVER_ROOT_URL` - Set to production URL (e.g., `https://grafana.yourdomain.com`)

- [ ] **Update Alertmanager SMTP** in `.env`:
  - [ ] `ALERTMANAGER_SMTP_FROM` - Your email address
  - [ ] `ALERTMANAGER_SMTP_USERNAME` - SMTP username
  - [ ] `ALERTMANAGER_SMTP_PASSWORD` - SMTP password (Gmail App Password)
  - [ ] `ALERTMANAGER_ALERT_EMAIL` - Email to receive alerts

- [ ] **Generate Alertmanager config**:
  ```bash
  cd deployment/prod
  ./alertmanager/generate-alertmanager-config.sh
  ```

- [ ] **Verify monitoring variables** are in `.env`:
  - [ ] `PROMETHEUS_RETENTION_TIME`
  - [ ] `PROMETHEUS_CLUSTER_NAME`
  - [ ] `PROMETHEUS_ENVIRONMENT`

---

### 3. Docker Images

- [ ] **Verify Docker images** in `docker-compose.*.yml`:
  - [ ] API: `docker.io/amit11081994/fyi-widget-api:latest` ✅
  - [ ] Worker: `docker.io/amit11081994/fyi-widget-worker-service:latest` ✅
  - [ ] Monitoring services use standard images ✅

- [ ] **Images are available** in Docker registry:
  ```bash
  docker pull docker.io/amit11081994/fyi-widget-api:latest
  docker pull docker.io/amit11081994/fyi-widget-worker-service:latest
  ```

---

### 4. Network Configuration

- [ ] **Create Docker network** on VPS:
  ```bash
  docker network create fyi-widget-network
  ```

- [ ] **Verify network** is external in all docker-compose files ✅

---

### 5. Port Exposure

- [ ] **Review port bindings**:
  - [ ] API Service: `127.0.0.1:8005:8005` - Keep as-is (reverse proxy handles)
  - [ ] Grafana: `127.0.0.1:3000:3000` - Keep internal, expose via reverse proxy
  - [ ] All other services on `127.0.0.1` - Keep internal ✅

- [ ] **Set up reverse proxy** (nginx):
  - [ ] Configure API endpoint
  - [ ] Configure Grafana endpoint
  - [ ] Set up SSL/TLS certificates

---

### 6. Database Configuration

- [ ] **Verify database credentials** in `.env`:
  - [ ] `MONGODB_USERNAME` and `MONGODB_PASSWORD`
  - [ ] `POSTGRES_USER` and `POSTGRES_PASSWORD`
  - [ ] `DATABASE_NAME` and `POSTGRES_DB`

- [ ] **Check database connection strings**:
  - [ ] `MONGODB_URL` - Uses internal Docker hostname
  - [ ] `POSTGRES_URL` - Uses internal Docker hostname

---

### 7. Security Checklist

- [ ] **Change default passwords**:
  - [ ] Grafana admin password
  - [ ] MongoDB password
  - [ ] PostgreSQL password
  - [ ] Admin API key

- [ ] **Secure `.env` file**:
  ```bash
  chmod 600 deployment/prod/.env
  ```

- [ ] **Verify `.env` is gitignored**:
  ```bash
  git check-ignore deployment/prod/.env
  # Should output: deployment/prod/.env
  ```

- [ ] **Review exposed ports**:
  - [ ] Only necessary ports exposed
  - [ ] Internal services on `127.0.0.1`

---

### 8. File Structure

- [ ] **All required files present**:
  - [ ] `docker-compose.api.yml`
  - [ ] `docker-compose.worker.yml`
  - [ ] `docker-compose.databases.yml`
  - [ ] `docker-compose.monitoring.yml`
  - [ ] `docker-compose.db-admins.yml` (optional)
  - [ ] All config directories (prometheus/, grafana/, etc.)
  - [ ] `generate-alertmanager-config.sh` script

---

### 9. Documentation

- [ ] **Review deployment docs**:
  - [ ] `VPS_PORT_EXPOSURE_GUIDE.md`
  - [ ] `MONITORING_ENV_SETUP.md`
  - [ ] `README.md`

---

## 🚀 Deployment Steps

### Step 1: Prepare VPS

```bash
# 1. Create directory structure
mkdir -p /opt/fyi-widget/deployment/prod
cd /opt/fyi-widget/deployment/prod

# 2. Upload all files from deployment/prod/
# 3. Create .env file
cp env.production.example .env
chmod 600 .env
nano .env  # Edit with production values

# 4. Generate Alertmanager config
./alertmanager/generate-alertmanager-config.sh
```

### Step 2: Create Docker Network

```bash
docker network create fyi-widget-network
```

### Step 3: Start Services (in order)

```bash
# 1. Start databases
docker-compose -f docker-compose.databases.yml up -d

# 2. Wait for databases to be ready (30 seconds)
sleep 30

# 3. Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# 4. Start API and Worker
docker-compose -f docker-compose.api.yml up -d
docker-compose -f docker-compose.worker.yml up -d

# 5. (Optional) Start admin UIs
docker-compose -f docker-compose.db-admins.yml up -d
```

### Step 4: Verify Services

```bash
# Check all containers are running
docker ps | grep fyi-widget

# Check API health
curl http://localhost:8005/health

# Check Grafana (if exposed)
curl http://localhost:3000/api/health

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

### Step 5: Configure Reverse Proxy

- Set up nginx/Apache
- Configure SSL certificates (Let's Encrypt)
- Proxy API and Grafana endpoints

---

## ⚠️ Critical Issues Found

### Issue 1: Missing Monitoring Variables in env.production.example ✅ FIXED

**Problem**: `env.production.example` doesn't include monitoring variables.

**Fix**: ✅ Added monitoring section to `env.production.example`:

```bash
# MONITORING: Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=CHANGE_THIS_SECURE_PASSWORD
GRAFANA_SERVER_ROOT_URL=https://grafana.yourdomain.com

# MONITORING: Alertmanager SMTP Configuration
ALERTMANAGER_SMTP_HOST=smtp.gmail.com
ALERTMANAGER_SMTP_PORT=587
ALERTMANAGER_SMTP_FROM=alerts@yourdomain.com
ALERTMANAGER_SMTP_USERNAME=alerts@yourdomain.com
ALERTMANAGER_SMTP_PASSWORD=CHANGE_THIS_APP_PASSWORD
ALERTMANAGER_SMTP_REQUIRE_TLS=true
ALERTMANAGER_ALERT_EMAIL=alerts@yourdomain.com

# MONITORING: Prometheus Configuration
PROMETHEUS_RETENTION_TIME=30d
PROMETHEUS_CLUSTER_NAME=fyi-widget-production
PROMETHEUS_ENVIRONMENT=production
```

---

### Issue 2: POSTGRES_URL Format

**Problem**: `env.production.example` uses separate POSTGRES_* variables, but code expects `POSTGRES_URL`.

**Check**: Verify if `POSTGRES_URL` is required or if code can use separate variables.

---

### Issue 3: Database UI Credentials

**Problem**: `docker-compose.db-admins.yml` has default passwords.

**Fix**: Ensure these are set in `.env`:
- `DB_UI_USER`
- `DB_UI_PASSWORD`
- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`

---

## ✅ What's Good

1. ✅ **Docker images** configured correctly (pulling from registry)
2. ✅ **All services** reference `.env` file
3. ✅ **Network configuration** uses external network
4. ✅ **Port bindings** are correct (internal services on 127.0.0.1)
5. ✅ **Monitoring stack** properly configured
6. ✅ **All config files** present in prod directory
7. ✅ **Generation script** for Alertmanager config

---

## 📝 Final Checks Before Deployment

- [ ] `.env` file created with ALL required variables
- [ ] All passwords changed from defaults
- [ ] Alertmanager config generated
- [ ] Docker images are accessible
- [ ] Docker network created
- [ ] Reverse proxy configured (if needed)
- [ ] Firewall rules configured
- [ ] SSL certificates ready (if using HTTPS)

---

## 🎯 Ready for Deployment?

**Status**: ✅ **READY FOR VPS DEPLOYMENT**

**All fixes completed:**
1. ✅ Added monitoring variables to `env.production.example`
2. ✅ Added `POSTGRES_URL` to `env.production.example`
3. ✅ Documented database UI credentials setup
4. ✅ Created comprehensive deployment checklist

**Final Steps:**
1. Create `.env` on VPS from `env.production.example`
2. Generate Alertmanager config
3. Deploy services in order
4. Test all endpoints

**Ready to deploy! 🚀**

