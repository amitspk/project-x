# Diagnose MongoDB Network Issue

## Error: "endpoint with name fyi-widget-mongodb already exists"

This means MongoDB is already connected, but might be on a different network or there's a conflict.

## Diagnostic Commands (Run on VPS)

### Step 1: Check What Network MongoDB is On

```bash
# Check all networks MongoDB is connected to
docker inspect fyi-widget-mongodb --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}'
```

### Step 2: Check Network Details

```bash
# List all networks
docker network ls

# Check each network to see which containers are on it
docker network inspect bridge | grep -A 10 "fyi-widget-mongodb"
docker network inspect fyi-widget-network | grep -A 10 "fyi-widget-mongodb"
```

### Step 3: Verify Current Setup

```bash
# Check if MongoDB can actually reach PostgreSQL
docker exec fyi-widget-mongodb nslookup postgres 2>/dev/null || \
docker exec fyi-widget-mongodb getent hosts postgres 2>/dev/null || \
echo "Cannot resolve postgres hostname"

# Check if both are on the same network
docker network inspect fyi-widget-network --format '{{range .Containers}}{{.Name}} {{end}}'
```

## Solution: Disconnect and Reconnect

If MongoDB is on a different network:

```bash
# Disconnect from any network it might be on
docker network disconnect fyi-widget-network fyi-widget-mongodb 2>/dev/null || true
docker network disconnect bridge fyi-widget-mongodb 2>/dev/null || true

# Connect to correct network
docker network connect fyi-widget-network fyi-widget-mongodb

# Verify
docker network inspect fyi-widget-network | grep -A 10 "Containers"
```

## Alternative: Restart MongoDB Container

The cleanest way:

```bash
# Stop MongoDB
docker stop fyi-widget-mongodb

# Disconnect from all networks
docker network disconnect fyi-widget-network fyi-widget-mongodb --force 2>/dev/null || true

# Start MongoDB again (will connect to network from compose file)
docker-compose -f docker-compose.mongodb.yml up -d

# Verify
docker network inspect fyi-widget-network | grep -A 10 "Containers"
```

