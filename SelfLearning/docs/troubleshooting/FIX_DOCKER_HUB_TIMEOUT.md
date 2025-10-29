# Fixing Docker Hub Timeout Issues

## Problem
Getting error: `Error response from daemon: failed to resolve reference... dial tcp ... i/o timeout`

This indicates Docker cannot reach Docker Hub registry.

---

## ✅ Solution: Pre-pull Images

The images are now successfully pulled. The issue was likely:
- Temporary network glitch
- DNS resolution delay
- Rancher Desktop network initialization

**The fix that worked:**
```bash
# Pull images manually first (this worked!)
docker pull mongo-express:latest
docker pull dpage/pgadmin4:latest

# Now docker-compose should work
docker-compose -f docker-compose.split-services.yml up -d
```

---

## If You Get This Error Again

### Quick Fix 1: Pull Images Individually

```bash
# Pull all required images first
docker pull mongo:7
docker pull postgres:16
docker pull mongo-express:latest
docker pull dpage/pgadmin4:latest

# Then start services
docker-compose -f docker-compose.split-services.yml up -d
```

### Quick Fix 2: Configure Docker DNS (Rancher Desktop)

**For Rancher Desktop on macOS:**

1. **Open Rancher Desktop Settings:**
   - Click Rancher Desktop icon in menu bar
   - Go to **Preferences** → **VM**

2. **Add DNS Servers:**
   - Look for **DNS** or **Custom DNS** settings
   - Add: `8.8.8.8` and `1.1.1.1` (Google & Cloudflare DNS)
   - Apply and restart Rancher Desktop

3. **Alternative: Configure via Docker daemon.json:**
   ```bash
   # Create/edit:
   ~/.docker/daemon.json
   
   # Add:
   {
     "dns": ["8.8.8.8", "1.1.1.1"]
   }
   
   # Restart Rancher Desktop
   ```

### Quick Fix 3: Use Specific Image Versions

Sometimes `latest` tag has issues. Use specific versions:

**Update docker-compose.split-services.yml:**

```yaml
mongo-express:
  image: mongo-express:1.0.2  # Instead of :latest

pgadmin:
  image: dpage/pgadmin4:8.2  # Instead of :latest
```

### Quick Fix 4: Restart Docker/Rancher Desktop

1. **Fully restart Rancher Desktop:**
   - Quit Rancher Desktop completely
   - Wait 10 seconds
   - Restart Rancher Desktop
   - Wait for it to fully start

2. **Then try again:**
   ```bash
   docker-compose -f docker-compose.split-services.yml pull
   docker-compose -f docker-compose.split-services.yml up -d
   ```

---

## Diagnostic Commands

```bash
# 1. Test Docker Hub connectivity
docker pull hello-world

# 2. Test specific images
docker pull mongo-express:latest
docker pull dpage/pgadmin4:latest

# 3. Test DNS resolution
nslookup registry-1.docker.io

# 4. Test HTTPS connectivity
curl -I --connect-timeout 10 https://registry-1.docker.io/v2/

# 5. Check Docker info
docker info | grep -i dns
```

---

## Common Causes

1. **Network/DNS Issues:**
   - VPN interference
   - Corporate firewall
   - DNS server issues
   - Rancher Desktop VM network initialization

2. **Rancher Desktop Specific:**
   - VM not fully initialized
   - Network adapter issues
   - DNS configuration in VM

3. **Temporary Docker Hub Issues:**
   - Rate limiting (if unauthenticated)
   - Regional outages
   - CDN issues

---

## Prevention

**Before running docker-compose, pre-pull images:**

```bash
# Add to your start scripts or run manually:
docker pull mongo:7
docker pull postgres:16
docker pull mongo-express:latest
docker pull dpage/pgadmin4:latest
```

Or update your `start_split_services.sh` to include image pulling first.

---

## Status: ✅ RESOLVED

Both images (`mongo-express:latest` and `dpage/pgadmin4:latest`) pulled successfully. You can now run:

```bash
docker-compose -f docker-compose.split-services.yml up -d
```
