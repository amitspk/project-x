# What Was Deployed to Your VPS

## ✅ What IS Deployed

### 1. MongoDB Database
- **Container**: `blog-qa-mongodb`
- **Port**: 27017 (localhost only - not exposed to internet)
- **Purpose**: Stores your blog Q&A data
- **Admin UI**: ❌ **NOT deployed** (mongo-express)

### 2. PostgreSQL Database
- **Container**: `blog-qa-postgres`
- **Port**: 5432 (localhost only - not exposed to internet)
- **Purpose**: Stores publisher configurations
- **Admin UI**: ❌ **NOT deployed** (pgadmin)

---

## ❌ What is NOT Deployed

### Admin UIs (Mongo Express & pgAdmin)

**Why they weren't deployed:**
1. **Security**: Admin UIs expose your databases through web interfaces
2. **Production best practice**: Admin tools should be separate from production
3. **Minimal deployment**: We only deployed essential services

**Where they exist:**
- `docker-compose.split-services.yml` (development file - not used on VPS)

---

## 🔍 Verify What's Running on VPS

Run this on your VPS to see what's actually deployed:

```bash
# List all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Should show:
# blog-qa-mongodb    Up X minutes    127.0.0.1:27017->27017/tcp
# blog-qa-postgres   Up X minutes    127.0.0.1:5432->5432/tcp

# Check for admin UIs (should show nothing)
docker ps | grep -E "mongo-express|pgadmin"
```

---

## 🔧 How to Access Databases (Without Admin UIs)

### MongoDB Access

**Option 1: Command Line (via docker exec)**
```bash
# Connect to MongoDB shell
docker exec -it blog-qa-mongodb mongosh -u admin -p

# Or run commands directly
docker exec blog-qa-mongodb mongosh -u admin -p --eval "show dbs"
```

**Option 2: From Your Local Machine (via SSH tunnel)**
```bash
# Create SSH tunnel
ssh -L 27017:localhost:27017 username@vps-ip

# Then on another terminal, connect
mongosh mongodb://admin:password@localhost:27017/blog_qa_db?authSource=admin
```

### PostgreSQL Access

**Option 1: Command Line (via docker exec)**
```bash
# Connect to PostgreSQL
docker exec -it blog-qa-postgres psql -U postgres -d blog_qa_publishers

# Or run commands directly
docker exec blog-qa-postgres psql -U postgres -d blog_qa_publishers -c "SELECT version();"
```

**Option 2: From Your Local Machine (via SSH tunnel)**
```bash
# Create SSH tunnel
ssh -L 5432:localhost:5432 username@vps-ip

# Then connect using any PostgreSQL client
psql postgresql://postgres:password@localhost:5432/blog_qa_publishers
```

---

## 🆕 If You Want to Add Admin UIs (Optional)

**⚠️ Important Security Note:**
Admin UIs should ONLY be added if:
- You really need them
- You secure them properly (username/password, IP whitelist)
- You understand the security risks

### Option 1: Add to Existing Setup

Create `docker-compose.admin-uis.yml` on VPS:

```yaml
version: '3.8'

services:
  mongo-express:
    image: mongo-express:latest
    container_name: blog-qa-mongo-express
    restart: unless-stopped
    ports:
      - "127.0.0.1:8081:8081"  # Only localhost
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: ${MONGODB_USERNAME:-admin}
      ME_CONFIG_MONGODB_ADMINPASSWORD: ${MONGODB_PASSWORD}
      ME_CONFIG_MONGODB_URL: mongodb://${MONGODB_USERNAME:-admin}:${MONGODB_PASSWORD}@mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: CHANGE_THIS_SECURE_PASSWORD
    networks:
      - blog-qa-network
    depends_on:
      - mongodb

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: blog-qa-pgadmin
    restart: unless-stopped
    ports:
      - "127.0.0.1:5050:80"  # Only localhost
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: CHANGE_THIS_SECURE_PASSWORD
      PGADMIN_CONFIG_SERVER_MODE: 'False'
      PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: 'False'
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    networks:
      - blog-qa-network
    depends_on:
      - postgres

networks:
  blog-qa-network:
    name: blog-qa-network
    external: true

volumes:
  pgadmin_data:
```

**Deploy:**
```bash
# Note: Add mongodb and postgres services to above file, or connect to existing network

docker-compose -f docker-compose.admin-uis.yml up -d
```

**Access via SSH tunnel:**
```bash
# From local machine
ssh -L 8081:localhost:8081 -L 5050:localhost:5050 username@vps-ip

# Then visit in browser:
# http://localhost:8081  (Mongo Express)
# http://localhost:5050  (pgAdmin)
```

---

## 🎯 Recommended Approach

### For Production: Don't Use Admin UIs

**Use command line access instead:**
```bash
# MongoDB
docker exec -it blog-qa-mongodb mongosh -u admin -p

# PostgreSQL
docker exec -it blog-qa-postgres psql -U postgres -d blog_qa_publishers
```

**Benefits:**
- ✅ More secure (no web interface exposed)
- ✅ No additional containers to manage
- ✅ Lower resource usage
- ✅ Standard practice in production

### For Development: Use Admin UIs Locally

On your **local machine**, use `docker-compose.split-services.yml` which includes mongo-express and pgadmin for easier development.

---

## 📊 Summary

| Service | Deployed? | Port | Access Method |
|---------|-----------|------|---------------|
| MongoDB | ✅ Yes | 27017 | Command line via `docker exec` |
| PostgreSQL | ✅ Yes | 5432 | Command line via `docker exec` |
| Mongo Express | ❌ No | - | Not deployed (security) |
| pgAdmin | ❌ No | - | Not deployed (security) |

**This is the correct setup for production!** Admin UIs are nice for development but add security risk and resource usage in production.

