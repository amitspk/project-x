# How to Run the Complete Blog Q&A System

## 🎯 Overview
This guide provides step-by-step instructions to run the complete Blog Q&A system with all services.

---

## 📋 Prerequisites

### 1. System Requirements
- Docker and Docker Compose installed
- Python 3.11+ (for local development)
- OpenAI API Key
- 8GB RAM minimum
- Ports available: 8005 (API), 27017 (MongoDB), 5432 (PostgreSQL)

### 2. Environment Setup

**Option A: Using .env file (Recommended)**
```bash
# Create .env from template
cp env.example .env

# Edit .env and add your OpenAI API key
# Replace: OPENAI_API_KEY=sk-your-key-here
# With:    OPENAI_API_KEY=sk-proj-actual-key-here

# The .env file is gitignored for security
```

**Option B: Export directly**
```bash
# Export your OpenAI API key in terminal
export OPENAI_API_KEY="sk-your-key-here"

# Verify it's set
echo $OPENAI_API_KEY
```

---

## 🚀 Quick Start (Recommended - Using Docker Compose)

### Start All Services with One Command
```bash
# From the project root directory
docker-compose -f docker-compose.split-services.yml up -d

# View logs
docker-compose -f docker-compose.split-services.yml logs -f

# Check service status
docker-compose -f docker-compose.split-services.yml ps
```

### Stop All Services
```bash
docker-compose -f docker-compose.split-services.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.split-services.yml down -v
```

---

## 🔧 Manual Setup (Alternative - For Development)

### Step 1: Start Database Services

#### MongoDB
```bash
docker run -d \
  --name blog-qa-mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  -e MONGO_INITDB_DATABASE=blog_qa_db \
  -v mongodb_data:/data/db \
  mongo:7

# Verify MongoDB is running
docker ps | grep mongodb
docker logs blog-qa-mongodb

# Test connection
echo 'db.runCommand("ping").ok' | docker exec -i blog-qa-mongodb mongosh localhost:27017/test --quiet
```

#### PostgreSQL
```bash
docker run -d \
  --name blog-qa-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=blog_qa_publishers \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16

# Verify PostgreSQL is running
docker ps | grep postgres
docker logs blog-qa-postgres

# Test connection
docker exec -it blog-qa-postgres pg_isready -U postgres
```

### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install API service dependencies
cd api_service
pip install -r requirements.txt
cd ..

# Install worker service dependencies
cd worker_service
pip install -r requirements.txt
cd ..
```

### Step 3: Start Application Services

#### Option A: Using the Start Script
```bash
# Make the script executable
chmod +x start_split_services.sh

# Run the script
./start_split_services.sh
```

#### Option B: Manual Start

**Terminal 1 - API Service:**
```bash
source venv/bin/activate
export OPENAI_API_KEY="sk-your-key-here"
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_USERNAME="admin"
export MONGODB_PASSWORD="password123"
export DATABASE_NAME="blog_qa_db"
export POSTGRES_URL="postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers"
export API_SERVICE_PORT=8005

cd api_service
python run_server.py
```

**Terminal 2 - Worker Service:**
```bash
source venv/bin/activate
export OPENAI_API_KEY="sk-your-key-here"
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_USERNAME="admin"
export MONGODB_PASSWORD="password123"
export DATABASE_NAME="blog_qa_db"
export POSTGRES_URL="postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers"
export POLL_INTERVAL_SECONDS=5
export CONCURRENT_JOBS=1

cd worker_service
python run_worker.py
```

---

## 🌐 Access Points

### API Service
- **API Base URL**: http://localhost:8005
- **Swagger Docs**: http://localhost:8005/docs
- **ReDoc**: http://localhost:8005/redoc
- **Health Check**: http://localhost:8005/health
- **Metrics**: http://localhost:8005/metrics

### Database Web UIs
- **Mongo Express** (MongoDB UI): http://localhost:8081
  - Username: `admin`
  - Password: `password123`
  - Browse MongoDB databases, collections, and documents visually
- **pgAdmin** (PostgreSQL UI): http://localhost:5050
  - Email: `admin@admin.com`
  - Password: `admin123`
  - Manage PostgreSQL databases with a full-featured web interface

### MongoDB (Direct Connection)
- **Connection String**: `mongodb://admin:password123@localhost:27017/blog_qa_db`
- **Port**: 27017
- **Database**: blog_qa_db
- **Username**: admin
- **Password**: password123

### PostgreSQL (Direct Connection)
- **Connection String**: `postgresql://postgres:postgres@localhost:5432/blog_qa_publishers`
- **Port**: 5432
- **Database**: blog_qa_publishers
- **Username**: postgres
- **Password**: postgres

---

## 📊 Verify Services are Running

### Check Docker Services
```bash
# All services status
docker-compose -f docker-compose.split-services.yml ps

# Individual service logs
docker logs blog-qa-mongodb
docker logs blog-qa-postgres
docker logs blog-qa-api
docker logs blog-qa-worker

# Follow logs in real-time
docker logs -f blog-qa-api
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8005/health

# Get API docs
open http://localhost:8005/docs

# Test publisher creation
curl -X POST http://localhost:8005/api/v1/publishers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Publisher",
    "domain": "example.com",
    "is_active": true
  }'
```

### Check Database Connections

**MongoDB:**
```bash
# Access MongoDB shell
docker exec -it blog-qa-mongodb mongosh -u admin -p password123

# Inside mongosh:
use blog_qa_db
show collections
db.publishers.find().pretty()
```

**PostgreSQL:**
```bash
# Access PostgreSQL shell
docker exec -it blog-qa-postgres psql -U postgres -d blog_qa_publishers

# Inside psql:
\dt
SELECT * FROM publishers;
\q
```

---

## 🧪 Test the System

### 1. Create a Publisher
```bash
curl -X POST http://localhost:8005/api/v1/publishers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medium",
    "domain": "medium.com",
    "is_active": true,
    "custom_selectors": {
      "article_body": "article",
      "title": "h1",
      "author": ".author-name"
    }
  }'
```

### 2. Submit a Blog URL for Processing
```bash
curl -X POST http://localhost:8005/api/v1/blogs/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://medium.com/@author/article-title-123",
    "publisher_id": 1
  }'
```

### 3. Get Processing Status
```bash
# Replace {job_id} with the actual job ID from step 2
curl http://localhost:8005/api/v1/blogs/jobs/{job_id}
```

### 4. Query Generated Questions
```bash
curl http://localhost:8005/api/v1/blogs/questions?url=https://medium.com/@author/article-title-123
```

---

## 🛠️ Troubleshooting

### Port Already in Use
```bash
# Find process using port 8005
lsof -ti:8005

# Kill the process
kill -9 $(lsof -ti:8005)

# For MongoDB (27017) or PostgreSQL (5432)
kill -9 $(lsof -ti:27017)
kill -9 $(lsof -ti:5432)
```

### MongoDB Connection Issues
```bash
# Restart MongoDB
docker restart blog-qa-mongodb

# Check logs
docker logs blog-qa-mongodb

# Test connection
docker exec -it blog-qa-mongodb mongosh -u admin -p password123 --eval "db.adminCommand('ping')"
```

### PostgreSQL Connection Issues
```bash
# Restart PostgreSQL
docker restart blog-qa-postgres

# Check logs
docker logs blog-qa-postgres

# Test connection
docker exec -it blog-qa-postgres pg_isready -U postgres
```

### API Service Not Responding
```bash
# Check if service is running
docker ps | grep blog-qa-api

# View logs
docker logs blog-qa-api

# Restart service
docker restart blog-qa-api
```

### Worker Service Not Processing Jobs
```bash
# Check worker logs
docker logs -f blog-qa-worker

# Restart worker
docker restart blog-qa-worker

# Check pending jobs in MongoDB
docker exec -it blog-qa-mongodb mongosh -u admin -p password123 blog_qa_db --eval "db.processing_jobs.find({status: 'pending'}).pretty()"
```

### Clean Slate - Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose -f docker-compose.split-services.yml down -v

# Remove dangling volumes
docker volume prune -f

# Restart everything
docker-compose -f docker-compose.split-services.yml up -d
```

---

## 🔄 Common Operations

### View Real-time Logs
```bash
# All services
docker-compose -f docker-compose.split-services.yml logs -f

# Specific service
docker-compose -f docker-compose.split-services.yml logs -f api-service
docker-compose -f docker-compose.split-services.yml logs -f worker-service
```

### Restart a Specific Service
```bash
docker-compose -f docker-compose.split-services.yml restart api-service
docker-compose -f docker-compose.split-services.yml restart worker-service
```

### Scale Worker Service
```bash
# Run 3 worker instances
docker-compose -f docker-compose.split-services.yml up -d --scale worker-service=3
```

### Update and Rebuild Services
```bash
# Rebuild and restart
docker-compose -f docker-compose.split-services.yml up -d --build

# Rebuild specific service
docker-compose -f docker-compose.split-services.yml build api-service
docker-compose -f docker-compose.split-services.yml up -d api-service
```

### Backup Databases
```bash
# Backup MongoDB
docker exec blog-qa-mongodb mongodump \
  -u admin -p password123 \
  --authenticationDatabase admin \
  --db blog_qa_db \
  --out /tmp/backup

docker cp blog-qa-mongodb:/tmp/backup ./mongodb_backup_$(date +%Y%m%d)

# Backup PostgreSQL
docker exec blog-qa-postgres pg_dump \
  -U postgres blog_qa_publishers > ./postgres_backup_$(date +%Y%m%d).sql
```

---

## 📝 Environment Variables Reference

### Required Variables
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Optional Configuration (with defaults)
```bash
# API Service
export API_SERVICE_PORT=8005
export API_SERVICE_HOST="0.0.0.0"

# MongoDB
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_USERNAME="admin"
export MONGODB_PASSWORD="password123"
export DATABASE_NAME="blog_qa_db"

# PostgreSQL
export POSTGRES_URL="postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers"

# Worker
export POLL_INTERVAL_SECONDS=5
export CONCURRENT_JOBS=1
export MAX_RETRIES=3
export RETRY_DELAY_SECONDS=60
```

---

## 🎓 Usage Examples

### Complete Workflow Example
```bash
# 1. Start all services
docker-compose -f docker-compose.split-services.yml up -d

# 2. Wait for services to be healthy (30 seconds)
sleep 30

# 3. Create a publisher
PUBLISHER_ID=$(curl -s -X POST http://localhost:8005/api/v1/publishers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medium",
    "domain": "medium.com",
    "is_active": true
  }' | jq -r '.id')

echo "Publisher ID: $PUBLISHER_ID"

# 4. Submit a blog for processing
JOB_ID=$(curl -s -X POST http://localhost:8005/api/v1/blogs/process \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a\",
    \"publisher_id\": $PUBLISHER_ID
  }" | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# 5. Monitor job status
while true; do
  STATUS=$(curl -s http://localhost:8005/api/v1/blogs/jobs/$JOB_ID | jq -r '.status')
  echo "Job status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# 6. Get the generated questions
curl -s http://localhost:8005/api/v1/blogs/questions?url=https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a | jq
```

---

## 🔐 Production Considerations

### Security Checklist
- [ ] Change default database passwords
- [ ] Use strong passwords (20+ characters)
- [ ] Enable SSL/TLS for database connections
- [ ] Use environment-specific configuration
- [ ] Enable authentication on API endpoints
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Use secrets management (e.g., AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable API key authentication
- [ ] Set up monitoring and alerting

### Performance Tuning
```bash
# Increase worker concurrency
export CONCURRENT_JOBS=5

# Scale worker service
docker-compose -f docker-compose.split-services.yml up -d --scale worker-service=3

# Configure MongoDB connection pool
export MONGODB_MAX_POOL_SIZE=100
export MONGODB_MIN_POOL_SIZE=10

# Configure PostgreSQL connection pool
export POSTGRES_POOL_SIZE=20
export POSTGRES_MAX_OVERFLOW=10
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8005/docs
- **Project README**: See [README.md](./README.md)
- **Architecture Details**: See [SPLIT_SERVICES_ARCHITECTURE.md](./SPLIT_SERVICES_ARCHITECTURE.md)
- **Publisher Onboarding**: See [PUBLISHER_ONBOARDING_GUIDE.md](./PUBLISHER_ONBOARDING_GUIDE.md)

---

## 🆘 Getting Help

If you encounter issues:
1. Check the logs: `docker-compose -f docker-compose.split-services.yml logs -f`
2. Verify all services are healthy: `docker-compose -f docker-compose.split-services.yml ps`
3. Check environment variables are set correctly
4. Review the troubleshooting section above
5. Create an issue in the repository with logs and error messages

---

## 📄 License

This project is intended for production use. Please ensure all dependencies are properly licensed for your use case.

