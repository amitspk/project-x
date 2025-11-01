# Production Docker Compose Files

This directory contains production docker-compose files that pull pre-built images from Docker Hub.

## Files

- `docker-compose.api.yml` - API service (pulls from Docker Hub)
- `docker-compose.worker.yml` - Worker service (pulls from Docker Hub)
- `docker-compose.databases.yml` - MongoDB and PostgreSQL
- `docker-compose.db-admins.yml` - Mongo Express and pgAdmin

## Usage

All commands should be run from the `prod/` directory:

```bash
cd deployment/prod
```

### Start Databases
```bash
docker-compose -f docker-compose.databases.yml up -d
```

### Start Database Admin UIs
```bash
docker-compose -f docker-compose.db-admins.yml up -d
```

### Start API Service
```bash
docker-compose -f docker-compose.api.yml up -d
```

### Start Worker Service
```bash
docker-compose -f docker-compose.worker.yml up -d
```

### Pull Latest Images
```bash
docker-compose -f docker-compose.api.yml pull
docker-compose -f docker-compose.worker.yml pull
```

### Stop Services
```bash
docker-compose -f docker-compose.api.yml down
docker-compose -f docker-compose.worker.yml down
docker-compose -f docker-compose.db-admins.yml down
docker-compose -f docker-compose.databases.yml down
```

## Notes

- Ensure you have a `.env` file in the `prod/` directory with all required environment variables
- Images are pulled from `docker.io/amit11081994/fyi-widget-api:latest` and `docker.io/amit11081994/fyi-widget-worker-service:latest`
- The network `fyi-widget-network` must exist before starting services that use it (or let docker-compose create it for databases)

