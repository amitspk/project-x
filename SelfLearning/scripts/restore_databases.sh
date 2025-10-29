#!/bin/bash

###############################################################################
# Database Restore Script for Production
# Restores MongoDB and PostgreSQL databases from backups
###############################################################################

set -e

# Configuration
BACKUP_DIR="${HOME}/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

if [ $# -lt 2 ]; then
    print_error "Usage: $0 <mongodb_backup_file.tar.gz> <postgres_backup_file.sql.gz>"
    print_info "Example: $0 mongodb-20240101_120000.tar.gz postgres-20240101_120000.sql.gz"
    exit 1
fi

MONGODB_BACKUP="$1"
POSTGRES_BACKUP="$2"

print_warning "⚠️  WARNING: This will overwrite existing database data!"
print_warning "⚠️  Make sure you have a current backup before proceeding!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    print_info "Restore cancelled"
    exit 0
fi

# Restore MongoDB
print_info "Restoring MongoDB from ${MONGODB_BACKUP}..."
if [ ! -f "${BACKUP_DIR}/mongodb/${MONGODB_BACKUP}" ]; then
    print_error "MongoDB backup file not found: ${BACKUP_DIR}/mongodb/${MONGODB_BACKUP}"
    exit 1
fi

cd "${BACKUP_DIR}/mongodb"
tar -xzf "${MONGODB_BACKUP}"
BACKUP_DIR_NAME=$(basename "${MONGODB_BACKUP}" .tar.gz)
docker cp "${BACKUP_DIR_NAME}" blog-qa-mongodb-prod:/backup/restore
docker exec blog-qa-mongodb-prod mongorestore \
    --username "${MONGODB_USERNAME:-admin}" \
    --password "${MONGODB_PASSWORD}" \
    --authenticationDatabase admin \
    --drop \
    /backup/restore/${BACKUP_DIR_NAME}
rm -rf "${BACKUP_DIR_NAME}"
print_info "MongoDB restore completed"

# Restore PostgreSQL
print_info "Restoring PostgreSQL from ${POSTGRES_BACKUP}..."
if [ ! -f "${BACKUP_DIR}/postgres/${POSTGRES_BACKUP}" ]; then
    print_error "PostgreSQL backup file not found: ${BACKUP_DIR}/postgres/${POSTGRES_BACKUP}"
    exit 1
fi

gunzip -c "${BACKUP_DIR}/postgres/${POSTGRES_BACKUP}" | \
    docker exec -i blog-qa-postgres-prod psql \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-blog_qa_publishers}"
print_info "PostgreSQL restore completed"

print_info "Restore completed successfully!"

