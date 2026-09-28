import requests

url = "http://127.0.0.1:8123/api/fc-dispatches"
headers = {
    "Content-Type": "application/json",
    "X-User-Id": "1",
    "X-Company-Id": "2"
}
payload = {
    "source_warehouse_id": 3,
    "warehouse_ids": [14],
    "dispatch_type": "STANDARD",
    "items": [
        {
            "product_id": 1155,
            "quantity": 1
        }
    ]
}
try:
    r = requests.post(url, json=payload, headers=headers)
    print("Status:", r.status_code)
    print("Response:", r.text)
except Exception as e:
    print("Error:", e)
