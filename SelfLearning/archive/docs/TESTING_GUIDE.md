# 🧪 Testing Guide - Resilience Features

Complete guide to test Circuit Breaker and Rate Limiting implementations.

---

## 🚀 Quick Start

### **Option 1: Automated Test Script (Recommended)**

```bash
# 1. Start the API server (Terminal 1)
cd /Users/aks000z/Documents/personal_repo/SelfLearning
./venv/bin/python blog_manager/run_server.py --debug --port 8001

# 2. Run automated tests (Terminal 2)
./test_resilience_features.sh
```

The script will test:
- ✅ Health checks with circuit breaker status
- ✅ Rate limiting under normal usage
- ✅ Rate limiting when exceeded
- ✅ Error message format
- ✅ Different limits per endpoint
- ✅ Circuit breaker monitoring

---

### **Option 2: Manual Testing**

Follow the individual tests below for detailed testing.

---

## 📋 Manual Tests

### **Test 1: Start the API Server**

```bash
cd /Users/aks000z/Documents/personal_repo/SelfLearning
./venv/bin/python blog_manager/run_server.py --debug --port 8001
```

**Expected Output:**
```
🚀 Starting Blog Manager Microservice
📊 Version: 1.0.0
🔧 Debug Mode: True
✅ Database connection established
✅ Database health check passed
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Troubleshooting:**
- If port 8001 is in use: `lsof -ti:8001 | xargs kill -9`
- If MongoDB is not running: Start it first

---

### **Test 2: Health Check with Circuit Breakers**

```bash
curl -s http://localhost:8001/health | jq '.'
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-13T...",
  "details": {
    "database": {
      "status": "connected",
      "collections": [...]
    },
    "circuit_breakers": {
      "all_closed": true,
      "open_breakers": [],
      "details": {
        "llm_service": {
          "state": "closed",
          "failure_count": 0,
          "last_failure_time": null
        },
        "mongodb": {
          "state": "closed",
          "failure_count": 0,
          "last_failure_time": null
        },
        "vector_db": {
          "state": "closed",
          "failure_count": 0,
          "last_failure_time": null
        },
        "crawler": {
          "state": "closed",
          "failure_count": 0,
          "last_failure_time": null
        },
        "external_api": {
          "state": "closed",
          "failure_count": 0,
          "last_failure_time": null
        }
      }
    }
  }
}
```

**✅ Success Criteria:**
- Status is `"healthy"`
- All circuit breakers are `"closed"`
- `all_closed` is `true`

---

### **Test 3: Rate Limiting - Normal Usage**

```bash
# Make 3 requests (under the limit of 10/minute)
for i in {1..3}; do
  echo "Request $i:"
  curl -i -X POST http://localhost:8001/api/v1/qa/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "What is Python?"}' 2>&1 | grep -E "HTTP|X-RateLimit"
  echo ""
  sleep 1
done
```

**Expected Output:**
```
Request 1:
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1728826860

Request 2:
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1728826860

Request 3:
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1728826860
```

**✅ Success Criteria:**
- All requests return `200 OK`
- `X-RateLimit-Remaining` decreases with each request
- Headers are present in every response

---

### **Test 4: Rate Limiting - Exceed Limit**

```bash
# Make 12 rapid requests (will exceed limit of 10/minute)
echo "Making 12 rapid requests..."
for i in {1..12}; do
  response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8001/api/v1/qa/ask \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test $i\"}")
  
  if [ "$response" = "200" ]; then
    echo "Request $i: ✓ 200 OK"
  elif [ "$response" = "429" ]; then
    echo "Request $i: ✗ 429 Too Many Requests (RATE LIMITED)"
  else
    echo "Request $i: ? $response"
  fi
  
  sleep 0.2
done
```

**Expected Output:**
```
Request 1: ✓ 200 OK
Request 2: ✓ 200 OK
Request 3: ✓ 200 OK
...
Request 10: ✓ 200 OK
Request 11: ✗ 429 Too Many Requests (RATE LIMITED)
Request 12: ✗ 429 Too Many Requests (RATE LIMITED)
```

**✅ Success Criteria:**
- First 10 requests: `200 OK`
- Requests 11+: `429 Too Many Requests`
- Rate limiting kicks in after limit

---

### **Test 5: Rate Limit Error Message**

```bash
# First, exceed the rate limit
for i in {1..12}; do
  curl -s -X POST http://localhost:8001/api/v1/qa/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "Spam"}' > /dev/null
done

# Now check the error message
curl -s -X POST http://localhost:8001/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "This should be rate limited"}' | jq '.'
```

**Expected Response:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please slow down and try again later.",
  "details": {
    "limit": "10 per 1 minute",
    "endpoint": "/api/v1/qa/ask",
    "identifier": "ip"
  },
  "retry_after_seconds": 60
}
```

**✅ Success Criteria:**
- Clear error message
- Includes retry information
- Specifies the limit and endpoint

---

### **Test 6: Different Limits Per Endpoint**

```bash
# Test Q&A endpoint (10/minute)
echo "Q&A Endpoint:"
curl -i -X POST http://localhost:8001/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Test"}' 2>&1 | grep "X-RateLimit-Limit:"

sleep 2

# Test Blog lookup endpoint (100/minute)
echo "Blog Lookup Endpoint:"
curl -i "http://localhost:8001/api/v1/blogs/by-url?url=https://example.com" 2>&1 | grep "X-RateLimit-Limit:"

sleep 2

# Test Similar blogs endpoint (20/minute)
echo "Similar Blogs Endpoint:"
curl -i -X POST http://localhost:8001/api/v1/similar/blogs \
  -H "Content-Type: application/json" \
  -d '{"question_id": "test123", "blog_url": "https://example.com", "limit": 3}' 2>&1 | grep "X-RateLimit-Limit:"
```

**Expected Output:**
```
Q&A Endpoint:
X-RateLimit-Limit: 10

Blog Lookup Endpoint:
X-RateLimit-Limit: 100

Similar Blogs Endpoint:
X-RateLimit-Limit: 20
```

**✅ Success Criteria:**
- Each endpoint has correct rate limit
- Q&A: 10, Blog: 100, Similar: 20

---

### **Test 7: Rate Limit Reset (Wait Test)**

```bash
# 1. Exceed rate limit
echo "Exceeding rate limit..."
for i in {1..12}; do
  curl -s -X POST http://localhost:8001/api/v1/qa/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "Test"}' > /dev/null
done

# 2. Verify we're rate limited
echo "Checking rate limit status..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8001/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Should be blocked"}')

if [ "$response" = "429" ]; then
  echo "✓ Currently rate limited (429)"
else
  echo "✗ Not rate limited (unexpected)"
fi

# 3. Wait for reset (60 seconds)
echo "Waiting 60 seconds for rate limit to reset..."
sleep 60

# 4. Try again
echo "Testing after reset..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8001/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "After reset"}')

if [ "$response" = "200" ]; then
  echo "✓ Rate limit reset successfully (200 OK)"
else
  echo "✗ Still rate limited (unexpected)"
fi
```

**Expected Output:**
```
Exceeding rate limit...
Checking rate limit status...
✓ Currently rate limited (429)
Waiting 60 seconds for rate limit to reset...
Testing after reset...
✓ Rate limit reset successfully (200 OK)
```

**✅ Success Criteria:**
- Rate limit blocks requests after exceeding
- After 60 seconds, requests work again

---

### **Test 8: Circuit Breaker - Simulate Failure (Advanced)**

This test simulates an LLM service failure to trigger the circuit breaker.

```bash
# 1. Check initial circuit breaker state
echo "Initial circuit breaker state:"
curl -s http://localhost:8001/health | jq '.details.circuit_breakers.details.llm_service'

# 2. Make a request that will fail (invalid API key scenario)
# Note: This requires temporarily breaking the LLM service
# For now, we'll just verify the circuit breaker is monitoring

echo ""
echo "Circuit breakers are monitoring these services:"
curl -s http://localhost:8001/health | jq -r '.details.circuit_breakers.details | keys[]'
```

**Expected Output:**
```
Initial circuit breaker state:
{
  "state": "closed",
  "failure_count": 0,
  "last_failure_time": null
}

Circuit breakers are monitoring these services:
llm_service
mongodb
vector_db
crawler
external_api
```

**✅ Success Criteria:**
- Circuit breakers are initialized
- All services are being monitored
- Initial state is "closed" (healthy)

---

## 🎯 Success Checklist

After running all tests, verify:

- [ ] API server starts successfully
- [ ] Health endpoint returns circuit breaker status
- [ ] All circuit breakers start in "closed" state
- [ ] Rate limiting works under normal load
- [ ] Rate limiting blocks excess requests (429)
- [ ] Error messages are user-friendly
- [ ] Different endpoints have different limits
- [ ] Rate limits reset after the time window
- [ ] Response headers include rate limit info

---

## 🐛 Troubleshooting

### **Issue: Rate Limiting Not Working**

**Check:**
```bash
# Verify slowapi is installed
./venv/bin/pip list | grep slowapi

# Check if limiter is attached
curl -s http://localhost:8001/health | grep -i rate
```

**Fix:**
```bash
# Reinstall dependencies
./venv/bin/pip install slowapi
```

---

### **Issue: Circuit Breakers Not Showing in Health**

**Check:**
```bash
# Verify pybreaker is installed
./venv/bin/pip list | grep pybreaker

# Check health endpoint structure
curl -s http://localhost:8001/health | jq '.details | keys'
```

**Fix:**
```bash
# Reinstall dependencies
./venv/bin/pip install pybreaker
```

---

### **Issue: 429 Errors Too Aggressive**

**Adjust rate limits:**

Edit `blog_manager/core/rate_limiting.py`:
```python
class RateLimits:
    AI_GENERATION = "20/minute"  # Increased from 10
    READ_OPERATIONS = "200/minute"  # Increased from 100
```

Restart the server.

---

## 📊 Load Testing (Optional)

For more advanced load testing, use Apache Bench or wrk:

### **Apache Bench:**
```bash
# Install (if needed)
brew install apache2  # macOS

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 -p payload.json -T application/json \
  http://localhost:8001/api/v1/qa/ask
```

### **wrk (Better for high load):**
```bash
# Install
brew install wrk  # macOS

# Test with 10 threads, 100 connections for 30 seconds
wrk -t10 -c100 -d30s --latency \
  http://localhost:8001/health
```

---

## 📈 What to Monitor

During testing, watch for:

1. **Response Times**: Should stay under 200ms for health checks
2. **Rate Limit Headers**: Present in all responses
3. **Circuit Breaker States**: All "closed" under normal operation
4. **Error Messages**: Clear and helpful
5. **Memory Usage**: Stable (no leaks)

---

## 🎉 Expected Results

**After all tests pass:**

✅ **Rate Limiting Working**
- API protected from spam
- Clear error messages
- Automatic reset after time window

✅ **Circuit Breakers Monitoring**
- All services monitored
- Status visible in /health
- Ready to prevent cascade failures

✅ **Production Ready**
- Your API can handle abuse
- Services protected from failures
- Users get helpful feedback

---

## 🚀 Next Steps

Once all tests pass:

1. **Adjust rate limits** if needed for your use case
2. **Add Redis** for distributed rate limiting (optional)
3. **Continue with Authentication** (Fix #3)
4. **Set up monitoring** for production

---

**Questions or issues? Check the logs:**
```bash
tail -f logs/app.log  # If logging to file
# Or check console output
```

