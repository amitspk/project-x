# Fix Script on VPS - Quick Guide

## Option A: Manual Fix (Quickest - Do This Now)

**On your VPS, edit the script:**

```bash
# SSH to VPS
ssh username@your-vps-ip

# Edit the script
nano ~/blog-qa/scripts/deploy-databases.sh
# or if in deployment folder:
nano ~/deployment/scripts/deploy-databases.sh
```

**Find this line (around line 63-65):**
```bash
# Create network (if it doesn't exist)
print_info "Creating Docker network..."
docker network create fyi-widget-network 2>/dev/null || print_info "Network already exists"
```

**Replace it with:**
```bash
# Clean up any existing network that might cause conflicts
print_info "Checking for existing network..."
if docker network inspect fyi-widget-network > /dev/null 2>&1; then
    print_warning "Existing network found. Checking if it's safe to remove..."
    NETWORK_CONTAINERS=$(docker network inspect fyi-widget-network --format '{{len .Containers}}' 2>/dev/null || echo "0")
    if [ "$NETWORK_CONTAINERS" = "0" ]; then
        print_info "Removing existing network to avoid conflicts..."
        docker network rm fyi-widget-network 2>/dev/null || true
    else
        print_warning "Network is in use. Will try to use existing network."
    fi
fi

print_info "Docker Compose will create/manage the network automatically"
```

**Save:** `Ctrl+X`, then `Y`, then `Enter`

**Now run:**
```bash
./scripts/deploy-databases.sh
```

---

## Option B: Clean Up and Run (Even Quicker)

**Instead of editing, just clean up manually:**

```bash
# On VPS
cd ~/blog-qa  # or ~/deployment

# Stop containers
docker-compose -f docker-compose.mongodb.yml down 2>/dev/null || true
docker-compose -f docker-compose.postgres.yml down 2>/dev/null || true

# Remove network
docker network rm fyi-widget-network 2>/dev/null || true

# Now run script (even without update, it should work after cleanup)
./scripts/deploy-databases.sh
```

---

## Option C: Re-transfer Updated Package (Best for Future)

**On your local machine:**

```bash
cd /path/to/project-x/SelfLearning

# Recreate package with fixes
./create-deployment-package.sh
```

**Transfer only the updated script:**

```bash
# From local machine
scp scripts/deploy-databases.sh username@vps-ip:~/blog-qa/scripts/
# or
scp scripts/deploy-databases.sh username@vps-ip:~/deployment/scripts/
```

**On VPS, make it executable:**
```bash
chmod +x scripts/deploy-databases.sh
```

---

## Recommended: Use Option B (Quick Fix)

Just run these commands on VPS - no file transfer needed:

```bash
cd ~/blog-qa  # or wherever your deployment is

docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.postgres.yml down
docker network rm fyi-widget-network 2>/dev/null || true

# Now run the script
./scripts/deploy-databases.sh
```

This will work immediately!

