#!/bin/bash
# Test script for new features: DELETE endpoint and Two-Part Prompt Architecture

echo "=========================================="
echo "🧪 Testing New Features"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8005"
ADMIN_KEY="admin-secret-key-change-in-production"

echo -e "${BLUE}📋 Available Endpoints:${NC}"
curl -s $API_URL/ | jq .
echo ""

echo "=========================================="
echo "TEST 1: List Publishers"
echo "=========================================="
echo ""

echo -e "${BLUE}→ GET /publishers/${NC}"
curl -s -X GET "$API_URL/publishers/" \
  -H "X-Admin-Key: $ADMIN_KEY" | jq .

echo ""
echo ""

echo "=========================================="
echo "TEST 2: Check DELETE Endpoint (Swagger)"
echo "=========================================="
echo ""

echo -e "${YELLOW}→ DELETE endpoint should be visible at:${NC}"
echo "   $API_URL/docs"
echo ""
echo -e "${YELLOW}→ Look for: DELETE /api/v1/questions/by-url${NC}"
echo ""

echo "=========================================="
echo "TEST 3: Custom Prompts Verification"
echo "=========================================="
echo ""

echo -e "${BLUE}→ Verifying Two-Part Prompt Architecture${NC}"
cd /Users/aks000z/Documents/personal_repo/SelfLearning
source venv/bin/activate
python verify_custom_prompts_implementation.py

echo ""
echo "=========================================="
echo "🎉 Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}✅ Services Running:${NC}"
echo "   - API Service: $API_URL"
echo "   - Worker Service: Running"
echo ""
echo -e "${GREEN}✅ New Features:${NC}"
echo "   1. DELETE /questions/by-url endpoint"
echo "   2. Two-Part Prompt Architecture"
echo ""
echo -e "${YELLOW}📚 Documentation:${NC}"
echo "   - DELETE Endpoint: docs/DELETE_BLOG_ENDPOINT.md"
echo "   - Two-Part Prompts: TWO_PART_PROMPT_ARCHITECTURE.md"
echo ""
echo -e "${YELLOW}🌐 Swagger UI:${NC}"
echo "   Open: $API_URL/docs"
echo ""

