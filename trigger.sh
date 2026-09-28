#!/bin/bash
BASE="https://inventory-intelligence-system-bkr-jspl.onrender.com"

RES=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"test_admin","password":"password"}')

echo "Login Response: $RES"
TOKEN=$(echo $RES | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "No token!"
    exit 1
fi

echo "Dispatching..."
curl -s -X POST "$BASE/api/fc-dispatches/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dispatch_type": "STANDARD", "warehouse_ids": [2], "items": [{"product_id": 1, "quantity": 1}]}' > response.txt
cat response.txt
echo ""

echo "Fetching logs..."
curl -s "$BASE/api/debug/logs" | python3 -c '
import sys, json
data = json.load(sys.stdin)
for line in data.get("logs", []):
    print(line, end="")
' | tail -n 40
