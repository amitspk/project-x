# Monitoring Environment Variables Setup

This guide explains how to configure monitoring stack settings via `.env` file.

---

## 📋 Environment Variables Added

The following monitoring-related variables have been added to `env.example`:

### Grafana Configuration
- `GRAFANA_ADMIN_USER` - Grafana admin username (default: `admin`)
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin password (default: `admin`) ⚠️ **Change this!**
- `GRAFANA_SERVER_ROOT_URL` - Grafana server URL for external access (default: `http://localhost:3001`)
  - For production: `https://grafana.yourdomain.com`

### Alertmanager SMTP Configuration
- `ALERTMANAGER_SMTP_HOST` - SMTP server hostname (default: `smtp.gmail.com`)
- `ALERTMANAGER_SMTP_PORT` - SMTP server port (default: `587`)
- `ALERTMANAGER_SMTP_FROM` - From email address
- `ALERTMANAGER_SMTP_USERNAME` - SMTP username/email
- `ALERTMANAGER_SMTP_PASSWORD` - SMTP password (use App Password for Gmail)
- `ALERTMANAGER_SMTP_REQUIRE_TLS` - Require TLS (default: `true`)
- `ALERTMANAGER_ALERT_EMAIL` - Email address to receive alerts

### Prometheus Configuration
- `PROMETHEUS_RETENTION_TIME` - How long to keep metrics (default: `30d`)
  - Options: `7d`, `15d`, `30d`, `60d`, `90d`
- `PROMETHEUS_CLUSTER_NAME` - Cluster name label (default: `fyi-widget-production`)
- `PROMETHEUS_ENVIRONMENT` - Environment label (default: `production`)

---

## 🔧 Setup Instructions

### 1. Copy env.example to .env (if not already done)
```bash
cp env.example .env
```

### 2. Update .env with your monitoring settings

**Grafana:**
```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password-here  # ⚠️ Change this!
GRAFANA_SERVER_ROOT_URL=http://localhost:3001  # Or https://grafana.yourdomain.com for prod
```

**Alertmanager Email:**
```bash
ALERTMANAGER_SMTP_HOST=smtp.gmail.com
ALERTMANAGER_SMTP_PORT=587
ALERTMANAGER_SMTP_FROM=your-email@example.com
ALERTMANAGER_SMTP_USERNAME=your-email@example.com
ALERTMANAGER_SMTP_PASSWORD=your-app-password  # For Gmail, use App Password
ALERTMANAGER_SMTP_REQUIRE_TLS=true
ALERTMANAGER_ALERT_EMAIL=your-email@example.com
```

**Prometheus:**
```bash
PROMETHEUS_RETENTION_TIME=30d  # How long to keep metrics
PROMETHEUS_CLUSTER_NAME=fyi-widget-production
PROMETHEUS_ENVIRONMENT=production
```

---

## 📝 Generating Alertmanager Config

Alertmanager config file (`alertmanager/alertmanager.yml`) doesn't support environment variables directly. 

**Option 1: Use Generation Script (Recommended)**

Run the generation script to create `alertmanager.yml` from your `.env` file:

```bash
cd deployment/dev
./alertmanager/generate-alertmanager-config.sh
```

This reads your `.env` file and generates `alertmanager.yml` with the correct SMTP and email settings.

**Option 2: Manual Edit**

If you prefer, manually edit `alertmanager/alertmanager.yml` and update:
- `smtp_smarthost`
- `smtp_from`
- `smtp_auth_username`
- `smtp_auth_password`
- `to:` fields in all receivers

---

## 🔄 What Happens Automatically

These settings are automatically read from `.env`:

### Grafana
- Admin username and password ✅
- Server root URL ✅

### Prometheus
- Retention time ✅ (via docker-compose command)

### Alertmanager
- ⚠️ Requires running generation script OR manual edit

---

## 🚀 For VPS/Production Deployment

1. **Set up .env** with production values:
   ```bash
   GRAFANA_SERVER_ROOT_URL=https://grafana.yourdomain.com
   ALERTMANAGER_SMTP_* (your production email settings)
   ALERTMANAGER_ALERT_EMAIL=production-alerts@yourdomain.com
   ```

2. **Generate Alertmanager config:**
   ```bash
   ./alertmanager/generate-alertmanager-config.sh
   ```

3. **Update Prometheus labels manually** (if needed):
   Edit `prometheus/prometheus.yml`:
   ```yaml
   external_labels:
     cluster: 'your-production-cluster'
     environment: 'production'
   ```

4. **Start services:**
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

---

## ✅ Verification

After setup, verify:

1. **Grafana login** with your `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`
2. **Prometheus retention** - check retention time in Prometheus UI
3. **Email alerts** - trigger a test alert to verify email delivery

---

## 📚 Notes

- **Grafana password**: Must be changed from default `admin`
- **Gmail App Password**: For Gmail, use an App Password, not your regular password
- **Prometheus labels**: Currently require manual edit of `prometheus.yml` (YAML doesn't support env vars)
- **Alertmanager config**: Use generation script for easiest setup

