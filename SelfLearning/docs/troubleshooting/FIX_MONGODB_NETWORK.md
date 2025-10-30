# Fix: MongoDB Not on Network

## Problem

MongoDB container is running but not connected to `fyi-widget-network`.

## Quick Fix (Run on VPS)

### Step 1: Check Current Status

```bash
# See which network MongoDB is on
docker inspect fyi-widget-mongodb --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}'

# Check all networks
docker network ls
```

### Step 2: Connect MongoDB to Network

```bash
# Connect MongoDB container to the network
docker network connect fyi-widget-network fyi-widget-mongodb

# Verify
docker network inspect fyi-widget-network | grep -A 5 "Containers"
```

Now you should see both containers!

### Step 3: Verify It Works

```bash
# Test connectivity
docker exec fyi-widget-mongodb getent hosts postgres
docker exec fyi-widget-postgres ping -c 2 mongodb
```

---

## Why This Happened

This usually happens if:
1. MongoDB was started before the network existed
2. MongoDB compose file wasn't using the named network correctly
3. Containers were started separately

---

## Permanent Fix

To prevent this in the future, ensure MongoDB compose file uses the network correctly.

**Check your docker-compose.mongodb.yml on VPS:**

The `networks` section should have:
```yaml
networks:
  fyi-widget-network:
    name: fyi-widget-network
```

Then restart MongoDB:
```bash
docker-compose -f docker-compose.mongodb.yml down
docker-compose -f docker-compose.mongodb.yml up -d
```

---

## Verify Fix

```bash
# Check network membership
docker network inspect fyi-widget-network | grep -A 10 "Containers"

# Should show both:
# fyi-widget-mongodb
# fyi-widget-postgres
```

