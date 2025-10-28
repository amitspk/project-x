# Quick Start - Split Services Architecture

**Get up and running in 5 minutes!** ⚡

---

## Prerequisites

- Python 3.11+
- MongoDB running on port 27017
- OpenAI API Key

---

## 🚀 Start in 3 Commands

```bash
# 1. Start MongoDB (if not running)
docker run -d -p 27017:27017 --name mongodb \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  mongo:7

# 2. Set your OpenAI API Key
export OPENAI_API_KEY=your-key-here

# 3. Start services
./start_split_services.sh
```

**Done!** API Service is now running on http://localhost:8005

---

## 🧪 Test It Works

```bash
./test_split_architecture.sh
```

This will:
1. ✅ Check services are healthy
2. ✅ Enqueue a test blog
3. ✅ Monitor processing
4. ✅ Verify questions were generated
5. ✅ Test Q&A endpoint

---

## 📖 API Examples

### Enqueue a Blog for Processing:
```bash
curl -X POST http://localhost:8005/api/v1/jobs/process \
  -H "Content-Type: application/json" \
  -d '{"blog_url": "https://medium.com/@user/article"}'
```

**Response** (202 Accepted):
```json
{
  "job_id": "abc-123",
  "status": "queued",
  "blog_url": "https://..."
}
```

### Check Job Status:
```bash
curl http://localhost:8005/api/v1/jobs/status/abc-123
```

### Get Processed Questions:
```bash
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://..."
```

### Ask a Custom Question:
```bash
curl -X POST http://localhost:8005/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is microservices?"}'
```

---

## 📊 Monitor

### Health Check:
```bash
curl http://localhost:8005/health
```

### Queue Statistics:
```bash
curl http://localhost:8005/api/v1/jobs/stats
```

### View Logs:
```bash
tail -f api_service.log
tail -f worker_service.log
```

---

## 🛑 Stop Services

```bash
pkill -f 'api_service|worker_service'
```

Or find and kill specific PIDs:
```bash
ps aux | grep -E 'api_service|worker_service'
kill <PID>
```

---

## 🐳 Docker Alternative

Prefer Docker? Use Docker Compose:

```bash
# Start
docker-compose -f docker-compose.split-services.yml up -d

# Logs
docker-compose logs -f api-service
docker-compose logs -f worker-service

# Stop
docker-compose down
```

---

## 📚 Full Documentation

For detailed information, see:
- `SPLIT_SERVICES_ARCHITECTURE.md` - Complete architecture guide
- `IMPLEMENTATION_STATUS_V3.md` - Implementation details

---

## 🆘 Troubleshooting

### Services won't start?
```bash
# Check MongoDB is running
nc -z localhost 27017

# Check API key is set
echo $OPENAI_API_KEY

# Check logs
cat api_service.log
cat worker_service.log
```

### Jobs not processing?
```bash
# Check worker is running
ps aux | grep worker_service

# Check queue
curl http://localhost:8005/api/v1/jobs/stats
```

---

## 🎯 What's Running?

| Service | Port | Purpose |
|---------|------|---------|
| **API Service** | 8005 | Fast reads + job enqueueing |
| **Worker Service** | - | Background blog processing |
| **MongoDB** | 27017 | Database + job queue |

---

**That's it! You're ready to go!** 🚀

For more details, check `SPLIT_SERVICES_ARCHITECTURE.md`

