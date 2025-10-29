#!/bin/bash

###############################################################################
# Database Backup Script for Production
# Backs up both MongoDB and PostgreSQL databases
###############################################################################

set -e

# Configuration
BACKUP_DIR="${HOME}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

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

# Create backup directory
mkdir -p "${BACKUP_DIR}/mongodb"
mkdir -p "${BACKUP_DIR}/postgres"

print_info "Starting database backups..."

# Backup MongoDB
print_info "Backing up MongoDB..."
if docker exec blog-qa-mongodb-prod mongodump \
    --username "${MONGODB_USERNAME:-admin}" \
    --password "${MONGODB_PASSWORD}" \
    --authenticationDatabase admin \
    --out /backup/mongodb-${DATE} 2>/dev/null; then
    
    docker cp blog-qa-mongodb-prod:/backup/mongodb-${DATE} "${BACKUP_DIR}/mongodb/"
    cd "${BACKUP_DIR}/mongodb"
    tar -czf mongodb-${DATE}.tar.gz mongodb-${DATE}
    rm -rf mongodb-${DATE}
    print_info "MongoDB backup completed: ${BACKUP_DIR}/mongodb/mongodb-${DATE}.tar.gz"
else
    print_error "MongoDB backup failed"
    exit 1
fi

# Backup PostgreSQL
print_info "Backing up PostgreSQL..."
if docker exec blog-qa-postgres-prod pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-blog_qa_publishers}" \
    > "${BACKUP_DIR}/postgres/postgres-${DATE}.sql" 2>/dev/null; then
    
    cd "${BACKUP_DIR}/postgres"
    gzip postgres-${DATE}.sql
    print_info "PostgreSQL backup completed: ${BACKUP_DIR}/postgres/postgres-${DATE}.sql.gz"
else
    print_error "PostgreSQL backup failed"
    exit 1
fi

# Cleanup old backups
print_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}/mongodb" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/postgres" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

print_info "Backup completed successfully!"

# Display backup sizes
echo ""
print_info "Backup sizes:"
du -h "${BACKUP_DIR}/mongodb/mongodb-${DATE}.tar.gz" 2>/dev/null || true
du -h "${BACKUP_DIR}/postgres/postgres-${DATE}.sql.gz" 2>/dev/null || true

