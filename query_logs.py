import requests
import json
import jwt
from datetime import datetime, timedelta, timezone

JWT_SECRET = "your-super-secret-key-change-in-prod"
payload = {
    "sub": "1",
    "username": "admin",
    "exp": datetime.now(timezone.utc) + timedelta(days=7),
}
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Test what happens if we send 26 items with duplicate file reference
items = [
    {"product_id": 475, "quantity": 48, "rate": 178.81, "gst_rate": 18.0, "matched_sku": "LG1041"},
    {"product_id": 475, "quantity": 48, "rate": 178.81, "gst_rate": 18.0, "matched_sku": "LG1041"} # Simulate second item
]

with open('../warehouse data/tally-upload bill.xlsx', 'rb') as f:
    res = requests.post(
        "http://127.0.0.1:8000/api/bulk-upload/tally-bill-confirm",
        files={"file": f},
        data={"warehouse_id": "1", "items": json.dumps(items)},
        headers={"x-company-id": "2", "Authorization": f"Bearer {token}"}
    )
print(res.status_code, res.text)
