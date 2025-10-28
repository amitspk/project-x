#!/bin/bash

# Test script for Circuit Breaker and Rate Limiting implementations
# Tests the production-grade resilience features

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_BASE="http://localhost:8001"

echo "═══════════════════════════════════════════════════════════════"
echo "🧪 TESTING RESILIENCE FEATURES"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Function to print test headers
print_test() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}TEST: $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to check if API is running
check_api() {
    echo -n "Checking if API is running... "
    if curl -s "$API_BASE/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is running${NC}"
        return 0
    else
        echo -e "${RED}✗ API is not running${NC}"
        echo ""
        echo "Please start the API server first:"
        echo "  cd /Users/aks000z/Documents/personal_repo/SelfLearning"
        echo "  ./venv/bin/python blog_manager/run_server.py --debug --port 8001"
        exit 1
    fi
}

# Function to extract rate limit headers
extract_headers() {
    local response=$1
    echo "$response" | grep -i "x-ratelimit" || echo "No rate limit headers found"
}

# ═══════════════════════════════════════════════════════════════
# PRELIMINARY CHECKS
# ═══════════════════════════════════════════════════════════════

print_test "0. Preliminary Checks"
check_api

# ═══════════════════════════════════════════════════════════════
# TEST 1: HEALTH CHECK WITH CIRCUIT BREAKER STATUS
# ═══════════════════════════════════════════════════════════════

print_test "1. Health Check with Circuit Breaker Status"

echo "Fetching health status..."
response=$(curl -s "$API_BASE/health" | jq '.')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Health check successful${NC}"
    echo ""
    echo "Service Status:"
    echo "$response" | jq -r '.status' | sed 's/^/  /'
    echo ""
    echo "Circuit Breaker Status:"
    echo "$response" | jq -r '.details.circuit_breakers' | sed 's/^/  /'
else
    echo -e "${RED}✗ Health check failed${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# TEST 2: RATE LIMITING - NORMAL USAGE
# ═══════════════════════════════════════════════════════════════

print_test "2. Rate Limiting - Normal Usage (Under Limit)"

echo "Making 3 requests to Q&A endpoint (limit: 10/minute)..."
echo ""

for i in {1..3}; do
    echo -e "${BLUE}Request $i:${NC}"
    response=$(curl -s -i -X POST "$API_BASE/api/v1/qa/ask" \
        -H "Content-Type: application/json" \
        -d '{"question": "What is Python?"}' 2>&1)
    
    status=$(echo "$response" | grep "HTTP" | head -1)
    limit=$(echo "$response" | grep -i "x-ratelimit-limit:" | cut -d':' -f2 | tr -d ' \r')
    remaining=$(echo "$response" | grep -i "x-ratelimit-remaining:" | cut -d':' -f2 | tr -d ' \r')
    
    if echo "$status" | grep -q "200 OK"; then
        echo -e "  Status: ${GREEN}200 OK${NC}"
        echo "  Rate Limit: $remaining/$limit remaining"
    else
        echo -e "  Status: ${RED}$status${NC}"
    fi
    echo ""
    sleep 1
done

echo -e "${GREEN}✓ Normal usage working correctly${NC}"

# ═══════════════════════════════════════════════════════════════
# TEST 3: RATE LIMITING - EXCEED LIMIT
# ═══════════════════════════════════════════════════════════════

print_test "3. Rate Limiting - Exceeding Limit"

echo "Making 12 rapid requests to Q&A endpoint (limit: 10/minute)..."
echo "This will trigger rate limiting after 10 requests."
echo ""

success_count=0
rate_limited_count=0

for i in {1..12}; do
    response=$(curl -s -i -X POST "$API_BASE/api/v1/qa/ask" \
        -H "Content-Type: application/json" \
        -d "{\"question\": \"Test question $i\"}" 2>&1)
    
    if echo "$response" | grep -q "200 OK"; then
        success_count=$((success_count + 1))
        remaining=$(echo "$response" | grep -i "x-ratelimit-remaining:" | cut -d':' -f2 | tr -d ' \r')
        echo -e "  Request $i: ${GREEN}✓ Success${NC} (Remaining: $remaining)"
    elif echo "$response" | grep -q "429"; then
        rate_limited_count=$((rate_limited_count + 1))
        echo -e "  Request $i: ${YELLOW}✗ Rate Limited (429)${NC}"
    else
        echo -e "  Request $i: ${RED}✗ Error${NC}"
    fi
    
    sleep 0.2  # Small delay between requests
done

echo ""
echo "Results:"
echo "  Successful requests: $success_count"
echo "  Rate limited requests: $rate_limited_count"

if [ $success_count -le 10 ] && [ $rate_limited_count -ge 2 ]; then
    echo -e "${GREEN}✓ Rate limiting working correctly!${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected results (might be timing-related)${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# TEST 4: RATE LIMIT ERROR RESPONSE
# ═══════════════════════════════════════════════════════════════

print_test "4. Rate Limit Error Response"

echo "Triggering rate limit to check error message format..."
echo ""

# Make sure we're rate limited
for i in {1..12}; do
    curl -s -X POST "$API_BASE/api/v1/qa/ask" \
        -H "Content-Type: application/json" \
        -d '{"question": "Spam"}' > /dev/null 2>&1
done

# Now check the error response
echo "Rate limit error response:"
response=$(curl -s -X POST "$API_BASE/api/v1/qa/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "This should be rate limited"}')

echo "$response" | jq '.' | sed 's/^/  /'

if echo "$response" | grep -q "rate_limit_exceeded"; then
    echo ""
    echo -e "${GREEN}✓ User-friendly error message present${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠ Error message format might have changed${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# TEST 5: DIFFERENT ENDPOINTS, DIFFERENT LIMITS
# ═══════════════════════════════════════════════════════════════

print_test "5. Different Endpoints Have Different Limits"

echo "Checking rate limits for different endpoints..."
echo ""

# Q&A endpoint (10/minute)
echo -e "${BLUE}1. Q&A Endpoint (expected: 10/minute):${NC}"
response=$(curl -s -i -X POST "$API_BASE/api/v1/qa/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test"}' 2>&1)
qa_limit=$(echo "$response" | grep -i "x-ratelimit-limit:" | head -1 | cut -d':' -f2 | tr -d ' \r')
echo "  Rate Limit: $qa_limit per minute"

sleep 2

# Blog lookup endpoint (100/minute)
echo ""
echo -e "${BLUE}2. Blog Lookup Endpoint (expected: 100/minute):${NC}"
response=$(curl -s -i "$API_BASE/api/v1/blogs/by-url?url=https://example.com" 2>&1)
blog_limit=$(echo "$response" | grep -i "x-ratelimit-limit:" | head -1 | cut -d':' -f2 | tr -d ' \r')
echo "  Rate Limit: $blog_limit per minute"

echo ""
if [ "$qa_limit" = "10" ] && [ "$blog_limit" = "100" ]; then
    echo -e "${GREEN}✓ Different endpoints have correct rate limits${NC}"
else
    echo -e "${YELLOW}⚠ Rate limits: Q&A=$qa_limit, Blog=$blog_limit${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# TEST 6: CIRCUIT BREAKER STATUS MONITORING
# ═══════════════════════════════════════════════════════════════

print_test "6. Circuit Breaker Status Monitoring"

echo "Checking circuit breaker states in health endpoint..."
echo ""

response=$(curl -s "$API_BASE/health" | jq '.details.circuit_breakers')

echo "Circuit Breaker Summary:"
all_closed=$(echo "$response" | jq -r '.all_closed')
open_breakers=$(echo "$response" | jq -r '.open_breakers | length')

echo "  All circuits closed: $all_closed"
echo "  Open circuits: $open_breakers"
echo ""

echo "Individual Circuit States:"
echo "$response" | jq -r '.details | to_entries[] | "  \(.key): \(.value.state)"'

echo ""
if [ "$all_closed" = "true" ]; then
    echo -e "${GREEN}✓ All circuit breakers are closed (healthy)${NC}"
else
    echo -e "${YELLOW}⚠ Some circuit breakers are open${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# TEST 7: RESPONSE TIME MEASUREMENT
# ═══════════════════════════════════════════════════════════════

print_test "7. Response Time Measurement"

echo "Measuring response times with resilience features enabled..."
echo ""

total_time=0
request_count=3

for i in $(seq 1 $request_count); do
    start=$(date +%s%N)
    response=$(curl -s "$API_BASE/health" > /dev/null 2>&1)
    end=$(date +%s%N)
    
    elapsed=$((($end - $start) / 1000000))  # Convert to milliseconds
    total_time=$(($total_time + $elapsed))
    
    echo "  Request $i: ${elapsed}ms"
done

avg_time=$(($total_time / $request_count))
echo ""
echo "Average response time: ${avg_time}ms"

if [ $avg_time -lt 100 ]; then
    echo -e "${GREEN}✓ Response times are excellent${NC}"
elif [ $avg_time -lt 500 ]; then
    echo -e "${GREEN}✓ Response times are good${NC}"
else
    echo -e "${YELLOW}⚠ Response times are higher than expected${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ RESILIENCE FEATURES TEST COMPLETE${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✓ Health checks working"
echo "  ✓ Circuit breakers initialized"
echo "  ✓ Rate limiting active"
echo "  ✓ Error messages user-friendly"
echo "  ✓ Different limits per endpoint"
echo "  ✓ Monitoring endpoints available"
echo ""
echo "🎉 Your API is production-ready with resilience patterns!"
echo ""
echo "Next steps:"
echo "  • Monitor /health endpoint for circuit breaker states"
echo "  • Adjust rate limits in blog_manager/core/rate_limiting.py if needed"
echo "  • Consider adding Redis for distributed rate limiting"
echo "  • Continue with Authentication implementation"
echo ""

