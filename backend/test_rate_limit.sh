#!/bin/bash

# Manual Testing Script for Rate Limiting (slowapi)
# This script demonstrates how to test the rate limiting manually
# Make sure the backend is running first: python main.py

API_URL="http://127.0.0.1:8000"
ENDPOINT="/analyze"

# Sample text for testing
SAMPLE_TEXT="This is a comprehensive test of the rate limiting functionality to ensure that the API properly restricts requests to one per five second interval."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Rate Limiting Test - Slowapi (1 request per 5 seconds)             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test 1: First request (should succeed)
echo -e "${YELLOW}[TEST 1]${NC} First request (should succeed - HTTP 200):"
echo -e "${YELLOW}Command:${NC} curl -X POST $API_URL$ENDPOINT -H \"Content-Type: application/json\" -d '{...}'"
echo ""

RESPONSE1=$(curl -s -w "\n%{http_code}" -X POST "$API_URL$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{
    \"content_type\": \"text\",
    \"text\": \"$SAMPLE_TEXT\"
  }")

HTTP_CODE1=$(echo "$RESPONSE1" | tail -n 1)
BODY1=$(echo "$RESPONSE1" | head -n -1)

if [ "$HTTP_CODE1" == "200" ]; then
  echo -e "${GREEN}✅ SUCCESS${NC} - HTTP $HTTP_CODE1"
  echo -e "${GREEN}Response:${NC} (truncated) $(echo $BODY1 | head -c 100)..."
else
  echo -e "${RED}❌ FAILED${NC} - HTTP $HTTP_CODE1"
  echo -e "${RED}Response:${NC} $BODY1"
fi
echo ""

# Test 2: Immediate second request (should be rate limited)
echo -e "${YELLOW}[TEST 2]${NC} Immediate second request (should be rate limited - HTTP 429):"
echo -e "${YELLOW}Command:${NC} curl -X POST $API_URL$ENDPOINT ... (immediately)"
echo ""

RESPONSE2=$(curl -s -w "\n%{http_code}" -X POST "$API_URL$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{
    \"content_type\": \"text\",
    \"text\": \"$SAMPLE_TEXT\"
  }")

HTTP_CODE2=$(echo "$RESPONSE2" | tail -n 1)
BODY2=$(echo "$RESPONSE2" | head -n -1)

if [ "$HTTP_CODE2" == "429" ]; then
  echo -e "${GREEN}✅ SUCCESS${NC} - HTTP $HTTP_CODE2 (Rate Limited as expected)"
  echo -e "${GREEN}Response:${NC} (truncated) $(echo $BODY2 | head -c 100)..."
else
  echo -e "${RED}❌ FAILED${NC} - Expected HTTP 429, got HTTP $HTTP_CODE2"
fi
echo ""

# Test 3: Wait and retry
echo -e "${YELLOW}[TEST 3]${NC} Wait 5 seconds and retry (should succeed - HTTP 200):"
echo -e "${YELLOW}Command:${NC} sleep 5 && curl -X POST $API_URL$ENDPOINT ..."
echo ""

echo -e "${BLUE}⏳ Waiting 5 seconds...${NC}"
for i in {1..5}; do
  echo -ne "\r⏳ Waiting $i/5 seconds..."
  sleep 1
done
echo ""

RESPONSE3=$(curl -s -w "\n%{http_code}" -X POST "$API_URL$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{
    \"content_type\": \"text\",
    \"text\": \"$SAMPLE_TEXT\"
  }")

HTTP_CODE3=$(echo "$RESPONSE3" | tail -n 1)
BODY3=$(echo "$RESPONSE3" | head -n -1)

if [ "$HTTP_CODE3" == "200" ]; then
  echo -e "${GREEN}✅ SUCCESS${NC} - HTTP $HTTP_CODE3 (Rate limit recovered)"
  echo -e "${GREEN}Response:${NC} (truncated) $(echo $BODY3 | head -c 100)..."
else
  echo -e "${RED}❌ FAILED${NC} - Expected HTTP 200, got HTTP $HTTP_CODE3"
fi
echo ""

# Summary
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                          TEST SUMMARY                                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

PASSED=0
FAILED=0

if [ "$HTTP_CODE1" == "200" ]; then
  echo -e "${GREEN}✅${NC} Test 1 (First request): PASSED"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌${NC} Test 1 (First request): FAILED"
  FAILED=$((FAILED + 1))
fi

if [ "$HTTP_CODE2" == "429" ]; then
  echo -e "${GREEN}✅${NC} Test 2 (Rate limited): PASSED"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌${NC} Test 2 (Rate limited): FAILED"
  FAILED=$((FAILED + 1))
fi

if [ "$HTTP_CODE3" == "200" ]; then
  echo -e "${GREEN}✅${NC} Test 3 (Recovery): PASSED"
  PASSED=$((PASSED + 1))
else
  echo -e "${RED}❌${NC} Test 3 (Recovery): FAILED"
  FAILED=$((FAILED + 1))
fi

echo ""
echo -e "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo ""

# Additional manual test options
echo -e "${BLUE}Additional Manual Tests:${NC}"
echo ""
echo "1. Test with different IPs (requires proxy or localhost simulation):"
echo "   This would test that rate limiting is per-IP"
echo ""
echo "2. Test different rate limit thresholds:"
echo "   Modify @limiter.limit(\"1/5seconds\") in routes.py to test different rates"
echo ""
echo "3. Test health endpoint (no rate limit):"
echo "   curl -X GET http://127.0.0.1:8000/"
echo ""

# Health check (no rate limit)
echo -e "${YELLOW}[BONUS]${NC} Testing health endpoint (should have no rate limit):"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)

if [ "$HEALTH_CODE" == "200" ]; then
  echo -e "${GREEN}✅ Health check: PASSED (HTTP $HEALTH_CODE)${NC}"
else
  echo -e "${RED}❌ Health check: FAILED (HTTP $HEALTH_CODE)${NC}"
fi
