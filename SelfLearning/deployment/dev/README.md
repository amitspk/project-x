# Development Docker Compose Files

This directory contains development versions of the docker-compose files that build from local Dockerfiles instead of pulling images from Docker Hub.

## Files

- `docker-compose.api.yml` - API service (builds from local Dockerfile)
- `docker-compose.worker.yml` - Worker service (builds from local Dockerfile)
- `docker-compose.databases.yml` - MongoDB and PostgreSQL (uses standard images)
- `docker-compose.db-admins.yml` - Mongo Express and pgAdmin (uses standard images)

## Usage

All commands should be run from the `dev/` directory:

```bash
cd deployment/dev
```

### Start Databases
```bash
docker-compose -f docker-compose.databases.yml up -d
```

### Start Database Admin UIs
```bash
docker-compose -f docker-compose.db-admins.yml up -d
```

### Start API Service (builds from local)
```bash
docker-compose -f docker-compose.api.yml up -d --build
```

### Start Worker Service (builds from local)
```bash
docker-compose -f docker-compose.worker.yml up -d --build
```

### Start All Services
```bash
# 1. Start databases
docker-compose -f docker-compose.databases.yml up -d

# 2. Start admin UIs
docker-compose -f docker-compose.db-admins.yml up -d

# 3. Build and start API and Worker
docker-compose -f docker-compose.api.yml up -d --build
docker-compose -f docker-compose.worker.yml up -d --build
```

### Rebuild After Code Changes
```bash
# Rebuild API
docker-compose -f docker-compose.api.yml build --no-cache
docker-compose -f docker-compose.api.yml up -d

# Rebuild Worker
docker-compose -f docker-compose.worker.yml build --no-cache
docker-compose -f docker-compose.worker.yml up -d
```

### Stop Services
```bash
docker-compose -f docker-compose.api.yml down
docker-compose -f docker-compose.worker.yml down
docker-compose -f docker-compose.db-admins.yml down
docker-compose -f docker-compose.databases.yml down
```

## Differences from Production

1. **Build Context**: Development files use `build` directive pointing to local Dockerfiles instead of `image` pulling from registry
2. **Build Context Path**: Uses `context: ../..` to reference the `SelfLearning/` directory (two levels up from `dev/`)
3. **Same Configuration**: All environment variables, networks, volumes, and other settings remain identical

## Notes

- Ensure you have a `.env` file in the `dev/` directory with all required environment variables
- The network `fyi-widget-network` must exist before starting services that use it (or let docker-compose create it for databases)
- Development builds will take longer on first run as they compile everything locally
- You can use the `test-dev-build.sh` script to quickly verify builds work correctly

