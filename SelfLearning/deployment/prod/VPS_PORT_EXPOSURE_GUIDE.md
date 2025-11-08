# VPS Port Exposure Guide - Monitoring Stack

## 📊 New Endpoints from Monitoring Stack

With the monitoring stack, you now have several new services that may need to be exposed on your VPS.

---

## ✅ **MUST EXPOSE** (Public Access Required)

### 1. Grafana Dashboard
- **Port**: `3000`
- **Service**: Grafana
- **Purpose**: Access monitoring dashboards
- **URL**: `http://your-vps-ip:3000` or `https://grafana.yourdomain.com`
- **Access**: Web UI for viewing metrics and logs
- **Security**: ⚠️ **Enable authentication** (default: admin/admin - CHANGE IT!)
- **Current Binding**: `127.0.0.1:3000:3000` → Change to `0.0.0.0:3000:3000` or use reverse proxy

**Recommendation**: Expose via reverse proxy (nginx) with SSL/TLS

---

## ⚠️ **OPTIONAL** (Expose if Needed)

### 2. Prometheus UI
- **Port**: `9090`
- **Service**: Prometheus
- **Purpose**: Direct PromQL queries, alert management
- **URL**: `http://your-vps-ip:9090`
- **Access**: Advanced users for debugging/alerts
- **Security**: ⚠️ No built-in auth - protect with reverse proxy
- **Current Binding**: `127.0.0.1:9090:9090` → Change to `0.0.0.0:9090:9090` if needed

**Recommendation**: Keep internal (127.0.0.1) unless you need direct PromQL access. Access metrics via Grafana instead.

### 3. API Service Metrics Endpoint
- **Port**: `8005`
- **Service**: API Service
- **Endpoint**: `/metrics`
- **URL**: `http://your-vps-ip:8005/metrics`
- **Purpose**: Prometheus metrics endpoint (already exposed via API port)
- **Security**: ⚠️ Consider rate limiting or basic auth if exposed publicly
- **Current Binding**: `127.0.0.1:8005:8005` → Already exposed for API

**Note**: This is part of your API service, so it's already exposed if API is public.

### 4. Worker Service Metrics Endpoint
- **Port**: `8006`
- **Service**: Worker Service
- **Endpoint**: `/metrics`
- **URL**: `http://your-vps-ip:8006/metrics`
- **Purpose**: Prometheus metrics endpoint for worker
- **Security**: ⚠️ Should be internal only
- **Current Binding**: `127.0.0.1:8006:8006` → Keep internal

**Recommendation**: Keep internal (127.0.0.1). Prometheus scrapes via Docker network.

---

## 🔒 **KEEP INTERNAL** (Do NOT Expose)

These services should remain on `127.0.0.1` and only be accessible from within the VPS or Docker network:

### 1. Loki (Log Aggregation)
- **Port**: `3100`
- **Reason**: Only accessed by Grafana internally
- **Current**: `127.0.0.1:3100:3000` ✅ Keep as-is

### 2. Alertmanager
- **Port**: `9093`
- **Reason**: Only receives alerts from Prometheus internally
- **Current**: `127.0.0.1:9093:9093` ✅ Keep as-is

### 3. MongoDB Exporter
- **Port**: `9216`
- **Reason**: Only scraped by Prometheus internally
- **Current**: `127.0.0.1:9216:9216` ✅ Keep as-is

### 4. PostgreSQL Exporter
- **Port**: `9187`
- **Reason**: Only scraped by Prometheus internally
- **Current**: `127.0.0.1:9187:9187` ✅ Keep as-is

### 5. Node Exporter
- **Port**: `9100`
- **Reason**: Only scraped by Prometheus internally
- **Current**: `127.0.0.1:9100:9100` ✅ Keep as-is

### 6. Promtail
- **No Port Exposed**
- **Reason**: Only pushes logs to Loki internally
- **Current**: No port binding ✅ Correct

---

## 🔧 **Recommended Changes for VPS**

### Option 1: Expose Grafana Directly (Simple)

Update `docker-compose.monitoring.yml`:

```yaml
grafana:
  ports:
    - "0.0.0.0:3000:3000"  # Changed from 127.0.0.1:3000:3000
```

Then access at: `http://your-vps-ip:3000`

---

### Option 2: Use Reverse Proxy (Recommended - Production)

Keep Grafana internal and set up nginx reverse proxy:

```nginx
# /etc/nginx/sites-available/grafana
server {
    listen 80;
    server_name grafana.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Benefits**:
- SSL/TLS support (Let's Encrypt)
- Custom domain
- Better security
- Can add authentication

---

## 📋 Summary Table

| Service | Port | Current Binding | VPS Exposure | Recommendation |
|---------|------|-----------------|--------------|----------------|
| **Grafana** | 3000 | `127.0.0.1:3000` | ✅ **Expose** | Via reverse proxy with SSL |
| Prometheus | 9090 | `127.0.0.1:9090` | ⚠️ Optional | Keep internal, use Grafana |
| Alertmanager | 9093 | `127.0.0.1:9093` | ❌ Internal | Keep internal |
| Loki | 3100 | `127.0.0.1:3100` | ❌ Internal | Keep internal |
| API Service | 8005 | `127.0.0.1:8005` | ✅ Already exposed | Already public |
| Worker Metrics | 8006 | `127.0.0.1:8006` | ❌ Internal | Keep internal |
| MongoDB Exporter | 9216 | `127.0.0.1:9216` | ❌ Internal | Keep internal |
| PostgreSQL Exporter | 9187 | `127.0.0.1:9187` | ❌ Internal | Keep internal |
| Node Exporter | 9100 | `127.0.0.1:9100` | ❌ Internal | Keep internal |

---

## 🚀 Quick Setup for VPS

### Minimal Changes (Expose Grafana):

1. Update `docker-compose.monitoring.yml`:
   ```yaml
   grafana:
     ports:
       - "0.0.0.0:3000:3000"  # Change this line
   ```

2. Update Grafana config for external access:
   ```yaml
   grafana:
     environment:
       - GF_SERVER_ROOT_URL=http://your-vps-ip:3000
       # OR if using domain:
       - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
   ```

3. Restart Grafana:
   ```bash
   docker-compose -f docker-compose.monitoring.yml restart grafana
   ```

---

## 🔒 Security Considerations

### When Exposing Grafana:

1. **Change Default Password**:
   ```bash
   # Via Grafana UI or API
   curl -X PUT http://admin:admin@localhost:3000/api/user/password \
     -H "Content-Type: application/json" \
     -d '{"oldPassword": "admin", "newPassword": "your-secure-password"}'
   ```

2. **Enable Authentication**:
   - Already enabled by default
   - Consider OAuth/SSO for production

3. **Use Reverse Proxy with SSL**:
   - Set up Let's Encrypt certificate
   - Force HTTPS redirect

4. **Firewall Rules**:
   ```bash
   # Only allow necessary ports
   sudo ufw allow 80/tcp    # HTTP (for SSL)
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw allow 3000/tcp  # Grafana (if not using reverse proxy)
   ```

---

## 📝 Firewall Configuration

For VPS firewall, only open:

```bash
# Public Services
sudo ufw allow 80/tcp      # HTTP (for API/nginx)
sudo ufw allow 443/tcp     # HTTPS (for API/nginx)
sudo ufw allow 3000/tcp    # Grafana (if exposing directly)

# Internal Services (already protected by 127.0.0.1)
# No need to open: 9090, 9093, 3100, 9216, 9187, 9100, 8006
```

---

## ✅ Checklist for VPS Deployment

- [ ] Update Grafana port binding to `0.0.0.0:3000:3000` (or use reverse proxy)
- [ ] Update `GF_SERVER_ROOT_URL` in Grafana environment
- [ ] Change Grafana admin password
- [ ] Set up reverse proxy with SSL (recommended)
- [ ] Configure firewall rules
- [ ] Keep other monitoring services internal (127.0.0.1)
- [ ] Test Grafana access from external IP
- [ ] Verify metrics are being collected
- [ ] Check dashboards are loading correctly

---

## 🎯 Final Recommendation

**For Production VPS:**

1. **Expose Grafana via nginx reverse proxy** (with SSL)
   - Domain: `grafana.yourdomain.com`
   - Keep port binding as `127.0.0.1:3000:3000`
   - Configure nginx to proxy to localhost:3000

2. **Keep everything else internal**
   - All other monitoring services stay on `127.0.0.1`
   - Prometheus, exporters, Loki remain internal
   - Worker metrics endpoint remains internal

3. **API Service**
   - Already exposed (if your API is public)
   - Metrics endpoint at `/metrics` is also accessible

This setup provides:
- ✅ Secure access to monitoring dashboards
- ✅ Internal-only access for data collection
- ✅ SSL/TLS encryption
- ✅ Professional domain setup

