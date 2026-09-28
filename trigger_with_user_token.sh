#!/bin/bash
BASE="https://inventory-intelligence-system-bkr-jspl.onrender.com"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0X2FkbWluIiwiZXhwIjoxNzg4OTMzNjI3fQ.9uH0_i_LVyuUNy1kWmLbCZ0rSndOsIKHzLGh1lwk7Uo"

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
