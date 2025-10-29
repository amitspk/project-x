# Building and Pushing Docker Images to Registry

This guide shows how to build your images and push them to a registry, so you **don't need to copy source code to VPS**.

---

## Why Use Registry?

✅ **No source code on VPS** - More secure  
✅ **Fast deployment** - Just pull images (~100MB vs 500MB+ source)  
✅ **Version control** - Tagged images, easy rollback  
✅ **Professional** - Production best practice  

---

## Option 1: Docker Hub (Easiest)

### Step 1: Create Docker Hub Account

1. Go to https://hub.docker.com
2. Create free account
3. Create repository: `fyi-widget-api`
4. Create repository: `fyi-widget-worker-service`

### Step 2: Build and Push Images

```bash
# On your local machine (from project root)

# Build API image
docker build -t YOUR_DOCKERHUB_USERNAME/fyi-widget-api:latest -f fyi_widget_api/Dockerfile .

# Build Worker image
docker build -t YOUR_DOCKERHUB_USERNAME/fyi-widget-worker-service:latest -f fyi_widget_fyi_widget_worker_service/Dockerfile .

# Login to Docker Hub
docker login

# Push images
docker push YOUR_DOCKERHUB_USERNAME/fyi-widget-api:latest
docker push YOUR_DOCKERHUB_USERNAME/fyi-widget-worker-service:latest

# Tag specific version (recommended for production)
docker tag YOUR_DOCKERHUB_USERNAME/fyi-widget-api:latest YOUR_DOCKERHUB_USERNAME/fyi-widget-api:v1.0.0
docker tag YOUR_DOCKERHUB_USERNAME/fyi-widget-worker-service:latest YOUR_DOCKERHUB_USERNAME/fyi-widget-worker-service:v1.0.0

docker push YOUR_DOCKERHUB_USERNAME/fyi-widget-api:v1.0.0
docker push YOUR_DOCKERHUB_USERNAME/fyi-widget-worker-service:v1.0.0
```

### Step 3: On VPS - Use Registry Images

```bash
# Update docker-compose files to use images:
# In docker-compose.api.registry.yml:
#   image: YOUR_DOCKERHUB_USERNAME/fyi-widget-api:v1.0.0

# Pull and deploy
docker-compose -f docker-compose.api.registry.yml pull
docker-compose -f docker-compose.api.registry.yml up -d
```

---

## Option 2: GitHub Container Registry (Free Private)

### Setup

```bash
# Login with GitHub token
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and tag
docker build -t ghcr.io/YOUR_USERNAME/fyi-widget-api:latest -f fyi_widget_api/Dockerfile .
docker build -t ghcr.io/YOUR_USERNAME/fyi-widget-worker-service:latest -f fyi_widget_fyi_widget_worker_service/Dockerfile .

# Push
docker push ghcr.io/YOUR_USERNAME/fyi-widget-api:latest
docker push ghcr.io/YOUR_USERNAME/fyi-widget-worker-service:latest
```

---

## Quick Build Script

Create `scripts/build-and-push.sh`:

```bash
#!/bin/bash

# Configuration
REGISTRY="docker.io"  # or "ghcr.io"
USERNAME="YOUR_USERNAME"
VERSION="v1.0.0"

# Build API
echo "Building API image..."
docker build -t ${REGISTRY}/${USERNAME}/fyi-widget-api:${VERSION} -f fyi_widget_api/Dockerfile .
docker tag ${REGISTRY}/${USERNAME}/fyi-widget-api:${VERSION} ${REGISTRY}/${USERNAME}/fyi-widget-api:latest

# Build Worker
echo "Building Worker image..."
docker build -t ${REGISTRY}/${USERNAME}/fyi-widget-worker-service:${VERSION} -f fyi_widget_fyi_widget_worker_service/Dockerfile .
docker tag ${REGISTRY}/${USERNAME}/fyi-widget-worker-service:${VERSION} ${REGISTRY}/${USERNAME}/fyi-widget-worker-service:latest

# Push
echo "Pushing images..."
docker push ${REGISTRY}/${USERNAME}/fyi-widget-api:${VERSION}
docker push ${REGISTRY}/${USERNAME}/fyi-widget-api:latest
docker push ${REGISTRY}/${USERNAME}/fyi-widget-worker-service:${VERSION}
docker push ${REGISTRY}/${USERNAME}/fyi-widget-worker-service:latest

echo "✅ Done!"
```

---

## Deployment Package Approach (Recommended)

### Step 1: Create Deployment Package (Local)

```bash
# Run the script
./create-deployment-package.sh

# This creates: deployment/ folder (~1-5MB)
```

### Step 2: Transfer Only Deployment Package to VPS

```bash
# Transfer tiny package (1-5MB vs 500MB+ source)
scp -r deployment/ username@vps-ip:~/blog-qa

# Or create tarball first
./create-deployment-package.sh
scp deployment.tar.gz username@vps-ip:~/
```

### Step 3: On VPS

```bash
# Extract (if using tarball)
tar -xzf deployment.tar.gz
cd deployment

# Configure
cp env.production.example .env
nano .env  # Fill in passwords

# If using registry images, update compose files:
nano docker-compose.api.registry.yml  # Set YOUR_DOCKERHUB_USERNAME
nano docker-compose.worker.registry.yml  # Set YOUR_DOCKERHUB_USERNAME

# Deploy
./scripts/deploy-databases.sh
docker-compose -f docker-compose.api.registry.yml up -d
docker-compose -f docker-compose.worker.registry.yml up -d
```

---

## Comparison

| Method | Transfer Size | Source on VPS? | Update Speed |
|--------|--------------|---------------|--------------|
| **Full Copy** | 500MB+ | ✅ Yes | Slow |
| **Deployment Package** | 1-5MB | ❌ No | Fast |
| **Registry Images** | 100-200MB (first time) | ❌ No | Very Fast |

---

## Best Practice Workflow

1. **Development**: Use local docker-compose with `build:`
2. **Production**: Use registry images with `image:`
3. **Updates**: Build → Push → Pull on VPS (no source transfer!)

---

## Next Steps

1. ✅ Choose registry (Docker Hub recommended to start)
2. ✅ Build and push images
3. ✅ Create deployment package: `./create-deployment-package.sh`
4. ✅ Transfer to VPS (only 1-5MB!)
5. ✅ Deploy using registry images

No more copying entire project! 🎉


