# Quick Start Guide

## 🚀 Start All Services (Simplest Way)

```bash
# 1. Create .env file with your OpenAI API key
cp env.example .env

# 2. Edit .env and add your actual API key
# Open .env in any text editor and replace:
# OPENAI_API_KEY=sk-your-key-here
# with your actual key

# 3. Start everything
./start_all_services.sh
```

**Alternative (Without .env file):**
```bash
# Export directly in terminal
export OPENAI_API_KEY="sk-your-key-here"
./start_all_services.sh
```

That's it! All services (MongoDB, PostgreSQL, API, Worker) will start automatically.

## 🌐 Access Points

### Application Services
- **API Documentation**: http://localhost:8005/docs
- **Health Check**: http://localhost:8005/health
- **API Base URL**: http://localhost:8005

### Database UIs (Web Interfaces)
- **Mongo Express** (MongoDB UI): http://localhost:8081
  - Username: `admin`
  - Password: `password123`
- **pgAdmin** (PostgreSQL UI): http://localhost:5050
  - Email: `admin@admin.com`
  - Password: `admin123`

## 🛑 Stop Services

```bash
./stop_all_services.sh
```

Or manually:
```bash
docker-compose -f docker-compose.split-services.yml down
```

## 📋 Common Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.split-services.yml logs -f

# Specific service
docker-compose -f docker-compose.split-services.yml logs -f api-service
docker-compose -f docker-compose.split-services.yml logs -f worker-service
```

### Check Status
```bash
docker-compose -f docker-compose.split-services.yml ps
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.split-services.yml restart

# Specific service
docker-compose -f docker-compose.split-services.yml restart api-service
```

### Clean Restart (removes all data)
```bash
docker-compose -f docker-compose.split-services.yml down -v
./start_all_services.sh
```

## 🧪 Test the API

```bash
# Health check
curl http://localhost:8005/health

# Create a publisher
curl -X POST http://localhost:8005/api/v1/publishers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medium",
    "domain": "medium.com",
    "is_active": true
  }'

# Submit a blog for processing
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://medium.com/@author/article",
    "publisher_id": 1
  }'
```

## 📖 Full Documentation

For detailed information, troubleshooting, and advanced usage, see [HOW_TO_RUN.md](./HOW_TO_RUN.md)

## 🔧 Requirements

- Docker & Docker Compose
- OpenAI API Key (optional, but needed for LLM features)
- Ports available: 8005, 27017, 5432

