#!/bin/bash

###############################################################################
# Create Minimal Deployment Package for VPS
# This creates a small package with only deployment files (no source code)
###############################################################################

set -e

DEPLOY_DIR="deployment"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📦 Creating minimal deployment package..."

# Create deployment directory
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"/scripts
mkdir -p "$DEPLOY_DIR"/nginx

# Copy docker-compose files
echo "📋 Copying docker-compose files..."
cp docker-compose.mongodb.yml "$DEPLOY_DIR/"
cp docker-compose.postgres.yml "$DEPLOY_DIR/"
cp docker-compose.api.yml "$DEPLOY_DIR/"
cp docker-compose.worker.yml "$DEPLOY_DIR/"

# Copy environment templates
echo "📋 Copying environment templates..."
cp env.production.example "$DEPLOY_DIR/"

# Copy deployment scripts
echo "📋 Copying deployment scripts..."
cp scripts/deploy-databases.sh "$DEPLOY_DIR/scripts/"
cp scripts/deploy-api.sh "$DEPLOY_DIR/scripts/"
cp scripts/deploy-worker.sh "$DEPLOY_DIR/scripts/"
cp scripts/backup_databases.sh "$DEPLOY_DIR/scripts/" 2>/dev/null || true
cp scripts/restore_databases.sh "$DEPLOY_DIR/scripts/" 2>/dev/null || true

# Copy nginx configs if they exist
if [ -d "nginx" ]; then
    echo "📋 Copying nginx configs..."
    cp nginx/*.conf "$DEPLOY_DIR/nginx/" 2>/dev/null || true
fi

# Copy documentation
echo "📋 Copying documentation..."
cp VPS_DEPLOY_DATABASES.md "$DEPLOY_DIR/" 2>/dev/null || true
cp DEPLOY_INDEPENDENT_SERVICES.md "$DEPLOY_DIR/" 2>/dev/null || true
cp QUICK_DEPLOY_INDEPENDENT.md "$DEPLOY_DIR/" 2>/dev/null || true

# Create README
cat > "$DEPLOY_DIR/README.md" << 'EOF'
# Blog Q&A System - VPS Deployment Package

This is a minimal deployment package containing only configuration files and scripts.

## What's Included

- Docker Compose files for independent services
- Deployment scripts
- Environment templates
- Nginx configurations
- Documentation

## What's NOT Included

- Source code (not needed - uses Docker images)
- Dependencies (not needed - bundled in images)
- Build files (not needed)

## Quick Start

1. Transfer this folder to VPS:
   ```bash
   scp -r deployment/ username@vps-ip:~/blog-qa
   ```

2. SSH to VPS:
   ```bash
   ssh username@vps-ip
   cd ~/blog-qa
   ```

3. Configure environment:
   ```bash
   cp env.production.example .env
   nano .env  # Fill in passwords/keys
   chmod 600 .env
   ```

4. Deploy:
   ```bash
   ./scripts/deploy-databases.sh
   ./scripts/deploy-api.sh
   ./scripts/deploy-worker.sh
   ```

## Using Docker Images from Registry

If you're using pre-built images from Docker Hub:

1. Update docker-compose.api.yml:
   - Replace `build:` with `image: yourname/blog-qa-api:tag`

2. Update docker-compose.worker.yml:
   - Replace `build:` with `image: yourname/blog-qa-worker:tag`

3. Pull images:
   ```bash
   docker-compose -f docker-compose.api.yml pull
   docker-compose -f docker-compose.worker.yml pull
   ```

## Size

This package is only ~1-5MB (vs 500MB+ for full project)!
EOF

# Create .gitignore for deployment
cat > "$DEPLOY_DIR/.gitignore" << 'EOF'
.env
*.log
backups/
EOF

# Make scripts executable
chmod +x "$DEPLOY_DIR/scripts/"*.sh 2>/dev/null || true

# Create tarball
echo "📦 Creating deployment.tar.gz..."
tar -czf deployment.tar.gz "$DEPLOY_DIR"

# Show size
DEPLOY_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
TAR_SIZE=$(du -sh deployment.tar.gz | cut -f1)

echo ""
echo "✅ Deployment package created!"
echo ""
echo "📊 Package Info:"
echo "   Directory: $DEPLOY_DIR ($DEPLOY_SIZE)"
echo "   Tarball:   deployment.tar.gz ($TAR_SIZE)"
echo ""
echo "📤 Transfer to VPS:"
echo "   scp deployment.tar.gz username@vps-ip:~/"
echo ""
echo "📥 On VPS, extract:"
echo "   tar -xzf deployment.tar.gz"
echo "   cd deployment"
echo ""

