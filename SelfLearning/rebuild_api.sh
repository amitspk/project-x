#!/bin/bash

set -e

echo "============================================"
echo "🔧 Rebuilding API Service"
echo "============================================"

cd /Users/aks000z/Documents/personal_repo/SelfLearning

echo ""
echo "Step 1: Stopping API service..."
docker-compose -f docker-compose.split-services.yml stop api-service

echo ""
echo "Step 2: Building API service (with cache)..."
docker-compose -f docker-compose.split-services.yml build api-service

echo ""
echo "Step 3: Starting API service..."
docker-compose -f docker-compose.split-services.yml up -d api-service

echo ""
echo "Step 4: Waiting for service to start..."
sleep 5

echo ""
echo "Step 5: Testing the new endpoint..."
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  'http://localhost:8005/api/v1/questions/check-and-load?blog_url=https://www.technewsworld.com/story/why-amds-openai-deal-marks-a-new-era-for-ai-data-centers-179954.html' \
  -H 'X-API-Key: pub_wu_Zq9Tfd16Fr5EjfuOS_bepryva4sXY75hIN7x_lRs')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "Response Body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""
echo "HTTP Status Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ SUCCESS! Endpoint is working!"
    
    # Check processing_status
    STATUS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('result', {}).get('processing_status', 'unknown'))" 2>/dev/null)
    echo "Processing Status: $STATUS"
    
    if [ "$STATUS" == "ready" ]; then
        QUESTION_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('result', {}).get('questions', [])))" 2>/dev/null)
        echo "✅ Fast path activated! Questions returned: $QUESTION_COUNT"
    fi
else
    echo "❌ Endpoint returned HTTP $HTTP_CODE"
    echo "Check logs with: docker logs api-service-1 --tail 50"
fi

echo ""
echo "============================================"
echo "You can also check Swagger UI at:"
echo "http://localhost:8005/docs"
echo "============================================"

