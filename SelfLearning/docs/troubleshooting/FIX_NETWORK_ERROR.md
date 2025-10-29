# Fix: Docker Network Error

## Problem

```
WARN: a network with name blog-qa-network exists but was not created by compose.
Set `external: true` to use an existing network
```

This happens when the network is created manually, but compose expects to manage it.

---

## Quick Fix (On VPS)

### Step 1: Remove the existing network

```bash
# Stop any containers using the network first
docker-compose -f docker-compose.mongodb.yml down 2>/dev/null || true
docker-compose -f docker-compose.postgres.yml down 2>/dev/null || true

# Remove the conflicting network
docker network rm blog-qa-network 2>/dev/null || true

# Verify it's removed
docker network ls | grep blog-qa-network
# Should show nothing
```

### Step 2: Re-run deployment

```bash
./scripts/deploy-databases.sh
```

---

## Why This Happened

The script was creating the network manually with `docker network create`, but Docker Compose wants to manage networks itself.

**Fixed:** The script no longer creates the network manually - Docker Compose will create it automatically.

---

## If Error Persists

### Option A: Clean up and redeploy

```bash
# Stop everything
docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.postgres.yml down

# Remove network
docker network rm blog-qa-network 2>/dev/null || true

# Redeploy
./scripts/deploy-databases.sh
```

### Option B: Use external network

If you want to manage the network manually:

1. Create it once:
   ```bash
   docker network create blog-qa-network
   ```

2. Update both docker-compose files to use `external: true`:
   ```yaml
   networks:
     blog-qa-network:
       external: true
   ```

But the automatic approach (fixed) is better - let Docker Compose manage it.

---

**The fix is already applied to the script! Just remove the old network and redeploy.**

