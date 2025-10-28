#!/bin/bash

# Test script for Publisher Onboarding API

set -e

API_URL="http://localhost:8005"
BASE_URL="${API_URL}/api/v1"

echo "========================================"
echo "Publisher Onboarding System Test"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Onboard a new publisher
echo -e "${BLUE}Test 1: Onboarding a new publisher${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/publishers/onboard" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechBlog Inc",
    "domain": "techblog.com",
    "email": "admin@techblog.com",
    "config": {
      "questions_per_blog": 7,
      "llm_model": "gpt-4o-mini",
      "temperature": 0.8,
      "max_tokens": 2500,
      "generate_summary": true,
      "generate_embeddings": true,
      "daily_blog_limit": 50,
      "ui_theme_color": "#FF5733"
    },
    "subscription_tier": "pro"
  }')

echo "$RESPONSE" | jq '.'

# Extract publisher ID and API key
PUBLISHER_ID=$(echo "$RESPONSE" | jq -r '.publisher.id')
API_KEY=$(echo "$RESPONSE" | jq -r '.api_key')

echo ""
echo -e "${GREEN}✅ Publisher onboarded successfully${NC}"
echo -e "   Publisher ID: ${YELLOW}${PUBLISHER_ID}${NC}"
echo -e "   API Key: ${YELLOW}${API_KEY}${NC}"
echo ""

# Test 2: Get publisher by ID
echo -e "${BLUE}Test 2: Get publisher by ID${NC}"
curl -s "${BASE_URL}/publishers/${PUBLISHER_ID}" | jq '.'
echo ""

# Test 3: Get publisher by domain
echo -e "${BLUE}Test 3: Get publisher by domain${NC}"
curl -s "${BASE_URL}/publishers/by-domain/techblog.com" | jq '.'
echo ""

# Test 4: Get publisher config
echo -e "${BLUE}Test 4: Get publisher config${NC}"
curl -s "${BASE_URL}/publishers/${PUBLISHER_ID}/config" | jq '.'
echo ""

# Test 5: Update publisher config
echo -e "${BLUE}Test 5: Update publisher config${NC}"
curl -s -X PUT "${BASE_URL}/publishers/${PUBLISHER_ID}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "config": {
      "questions_per_blog": 10,
      "llm_model": "gpt-4o",
      "temperature": 0.7
    }
  }' | jq '.'
echo ""

# Test 6: List all publishers
echo -e "${BLUE}Test 6: List all publishers${NC}"
curl -s "${BASE_URL}/publishers/?page=1&page_size=10" | jq '.'
echo ""

# Test 7: Onboard Baeldung
echo -e "${BLUE}Test 7: Onboard Baeldung (for actual testing)${NC}"
BAELDUNG_RESPONSE=$(curl -s -X POST "${BASE_URL}/publishers/onboard" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baeldung",
    "domain": "baeldung.com",
    "email": "contact@baeldung.com",
    "config": {
      "questions_per_blog": 8,
      "llm_model": "gpt-4o-mini",
      "temperature": 0.75,
      "max_tokens": 3000,
      "generate_summary": true,
      "generate_embeddings": true,
      "daily_blog_limit": 100,
      "ui_theme_color": "#2ECC71"
    },
    "subscription_tier": "enterprise"
  }')

echo "$BAELDUNG_RESPONSE" | jq '.'

BAELDUNG_ID=$(echo "$BAELDUNG_RESPONSE" | jq -r '.publisher.id')
BAELDUNG_KEY=$(echo "$BAELDUNG_RESPONSE" | jq -r '.api_key')

echo ""
echo -e "${GREEN}✅ Baeldung onboarded successfully${NC}"
echo -e "   Publisher ID: ${YELLOW}${BAELDUNG_ID}${NC}"
echo -e "   API Key: ${YELLOW}${BAELDUNG_KEY}${NC}"
echo ""

# Test 8: Process a blog from Baeldung
echo -e "${BLUE}Test 8: Process a blog from Baeldung (should use 8 questions)${NC}"
JOB_RESPONSE=$(curl -s -X POST "${BASE_URL}/jobs/process" \
  -H "Content-Type: application/json" \
  -d '{
    "blog_url": "https://www.baeldung.com/java-threadlocal"
  }')

echo "$JOB_RESPONSE" | jq '.'

JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id')

echo ""
echo -e "${GREEN}✅ Job enqueued: ${JOB_ID}${NC}"
echo -e "${YELLOW}   Worker will use Baeldung's config (8 questions, gpt-4o-mini, temp 0.75)${NC}"
echo ""

# Test 9: Check job status
echo -e "${BLUE}Test 9: Check job status${NC}"
echo "Waiting for job to complete (checking every 5 seconds)..."
echo ""

for i in {1..20}; do
    STATUS_RESPONSE=$(curl -s "${BASE_URL}/jobs/status/${JOB_ID}")
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
    
    echo -e "${YELLOW}Attempt $i: Status = ${STATUS}${NC}"
    
    if [ "$STATUS" == "completed" ]; then
        echo ""
        echo -e "${GREEN}✅ Job completed successfully!${NC}"
        echo "$STATUS_RESPONSE" | jq '.'
        break
    elif [ "$STATUS" == "failed" ]; then
        echo ""
        echo -e "${RED}❌ Job failed!${NC}"
        echo "$STATUS_RESPONSE" | jq '.'
        break
    fi
    
    sleep 5
done

echo ""

# Test 10: Verify questions count
echo -e "${BLUE}Test 10: Verify questions were generated with correct count${NC}"
QUESTIONS_RESPONSE=$(curl -s "${BASE_URL}/questions/by-url?blog_url=https://www.baeldung.com/java-threadlocal")
QUESTION_COUNT=$(echo "$QUESTIONS_RESPONSE" | jq '.questions | length')

echo "Expected: 8 questions (as per Baeldung config)"
echo "Actual: ${QUESTION_COUNT} questions"

if [ "$QUESTION_COUNT" == "8" ]; then
    echo -e "${GREEN}✅ Correct number of questions generated!${NC}"
else
    echo -e "${RED}❌ Question count mismatch!${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}All Tests Completed!${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  - TechBlog Publisher ID: ${PUBLISHER_ID}"
echo "  - Baeldung Publisher ID: ${BAELDUNG_ID}"
echo "  - Test Job ID: ${JOB_ID}"
echo ""
echo "You can now:"
echo "  1. Check Chrome extension with the processed blog"
echo "  2. Verify 8 questions appear (not the default 5)"
echo "  3. Test other publishers with different configs"
echo ""

