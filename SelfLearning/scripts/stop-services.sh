#!/bin/bash

# Stop FYI Widget services (worker, API, DB admin UIs, databases)
# Usage:
#   ./scripts/stop-services.sh            # stop containers (keeps volumes/data)
#   ./scripts/stop-services.sh --volumes  # also remove volumes (DANGEROUS: wipes DB data)

set -euo pipefail

cd "$(dirname "$0")/.."

REMOVE_VOLUMES=false
if [[ ${1:-} == "--volumes" ]]; then
  REMOVE_VOLUMES=true
fi

echo "🔻 Stopping FYI Widget services..."

# 1) Stop worker
if $REMOVE_VOLUMES; then
  docker-compose -f docker-compose.worker.prod.yml down -v --remove-orphans || true
else
  docker-compose -f docker-compose.worker.prod.yml down --remove-orphans || true
fi

# 2) Stop API
if $REMOVE_VOLUMES; then
  docker-compose -f docker-compose.api.prod.yml down -v --remove-orphans || true
else
  docker-compose -f docker-compose.api.prod.yml down --remove-orphans || true
fi

# 3) Stop DB admin UIs (optional file; ignore if missing)
if [[ -f docker-compose.db-admins.prod.yml ]]; then
  if $REMOVE_VOLUMES; then
    docker-compose -f docker-compose.db-admins.prod.yml down -v --remove-orphans || true
  else
    docker-compose -f docker-compose.db-admins.prod.yml down --remove-orphans || true
  fi
fi

# 4) Stop databases (MongoDB, Postgres)
if $REMOVE_VOLUMES; then
  docker-compose -f docker-compose.databases.prod.yml down -v --remove-orphans || true
else
  docker-compose -f docker-compose.databases.prod.yml down --remove-orphans || true
fi

echo "✅ All services stopped."


