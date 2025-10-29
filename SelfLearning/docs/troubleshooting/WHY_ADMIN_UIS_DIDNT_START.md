# Why mongo-express and pgadmin Didn't Start Initially

## Problem

When you ran `docker-compose -f docker-compose.split-services.yml up -d`, the `mongo-express` and `pgadmin` containers didn't start automatically, even though they're defined in the compose file.

## Root Cause

**Docker Compose skips services if image pull fails during initial startup.**

Here's what happened:

1. **Initial network timeout**: When you first ran docker-compose, there was a network timeout trying to pull `mongo-express:latest` and `dpage/pgadmin4:latest` from Docker Hub
2. **Silent failure**: Docker Compose doesn't automatically retry failed image pulls during `docker-compose up`
3. **Service skipped**: If an image can't be pulled, Docker Compose skips creating that container entirely
4. **No error shown**: The command might complete "successfully" but those services just aren't started

## Why It Works When You Start Manually

When you run:
```bash
docker-compose -f docker-compose.split-services.yml up -d mongo-express
```

It works because:
- The images were already pulled successfully (we fixed the network issue)
- Docker Compose can now find the images locally
- The container creation succeeds

## Solution (Already Applied)

I've updated `start_all_services.sh` to:

1. **Pre-pull images** before starting services:
   ```bash
   docker-compose -f docker-compose.split-services.yml pull mongodb postgres mongo-express pgadmin
   ```

2. **Explicitly start admin UIs** after main services:
   ```bash
   docker-compose -f docker-compose.split-services.yml up -d mongo-express pgadmin
   ```

This ensures:
- Images are pulled first (catching network issues early)
- Admin UIs are explicitly started even if they were skipped initially
- Better error visibility if something fails

## How to Verify All Services Started

```bash
# Check all services are running
docker-compose -f docker-compose.split-services.yml ps

# Should show:
# - mongodb
# - postgres  
# - api-service
# - worker-service
# - mongo-express  ← Should be here now
# - pgadmin        ← Should be here now
```

## Manual Fix (If It Happens Again)

If admin UIs don't start:

```bash
# Option 1: Start them explicitly
docker-compose -f docker-compose.split-services.yml up -d mongo-express pgadmin

# Option 2: Pull images first, then start
docker-compose -f docker-compose.split-services.yml pull mongo-express pgadmin
docker-compose -f docker-compose.split-services.yml up -d mongo-express pgadmin

# Option 3: Restart everything
docker-compose -f docker-compose.split-services.yml down
docker-compose -f docker-compose.split-services.yml pull
docker-compose -f docker-compose.split-services.yml up -d
```

## Best Practice Going Forward

**Always use `start_all_services.sh` instead of direct docker-compose:**

```bash
# ✅ Good - handles all edge cases
./start_all_services.sh

# ⚠️  Might miss admin UIs if image pull fails
docker-compose -f docker-compose.split-services.yml up -d
```

The updated script now:
- Pre-pulls all images
- Starts all services
- Explicitly ensures admin UIs are running
- Shows better error messages

## Current Status

✅ **Both services are now running:**
- **mongo-express**: http://localhost:8081 (admin/password123)
- **pgadmin**: http://localhost:5050 (admin@admin.com/admin123)

**Note**: Use **HTTP** (not HTTPS) for both services - they don't use SSL in development.

