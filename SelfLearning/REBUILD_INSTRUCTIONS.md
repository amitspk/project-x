# 🔧 Rebuild Instructions for Check-and-Load Endpoint

## The new endpoint code is already in the file!

Location: `api_service/api/routers/questions_router.py` (line 43-217)

## Steps to Deploy:

### 1. Rebuild the API Service
```bash
cd /Users/aks000z/Documents/personal_repo/SelfLearning

docker-compose -f docker-compose.split-services.yml build --no-cache api-service
```

### 2. Restart the Service
```bash
docker-compose -f docker-compose.split-services.yml up -d --no-deps api-service
```

### 3. Wait for Service to Start
```bash
sleep 5
```

### 4. Verify the Endpoint is Available

#### Option A: Check Swagger UI
Open in browser:
```
http://localhost:8005/docs
```
Look for: `GET /api/v1/questions/check-and-load`

#### Option B: Check via cURL
```bash
curl -X GET \
  'http://localhost:8005/api/v1/questions/check-and-load?blog_url=https://www.technewsworld.com/story/why-amds-openai-deal-marks-a-new-era-for-ai-data-centers-179954.html' \
  -H 'X-API-Key: pub_wu_Zq9Tfd16Fr5EjfuOS_bepryva4sXY75hIN7x_lRs' \
  | python3 -m json.tool
```

#### Option C: Check OpenAPI Spec
```bash
curl -s http://localhost:8005/openapi.json | grep -A 5 "check-and-load"
```

### 5. Check Logs (if issues)
```bash
docker logs api-service-1 --tail 100
```

## Expected Response

If successful, you should see:
```json
{
  "status": "success",
  "status_code": 200,
  "message": "Questions loaded successfully",
  "result": {
    "processing_status": "ready",
    "blog_url": "...",
    "questions": [...]
  }
}
```

## Troubleshooting

### If endpoint not showing:
1. Check if container is running: `docker ps | grep api-service`
2. Check logs: `docker logs api-service-1 --tail 50`
3. Rebuild from scratch: `docker-compose -f docker-compose.split-services.yml up -d --build api-service`

### If getting 500 error:
1. Check container logs for Python errors
2. Verify MongoDB is running: `docker ps | grep mongodb`
3. Verify PostgreSQL is running: `docker ps | grep postgres`

