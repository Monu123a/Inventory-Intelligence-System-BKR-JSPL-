import requests

url = "https://inventory-intelligence-system-bkr-jspl.onrender.com/api/fc-dispatches"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0X2FkbWluIiwiZXhwIjoxNzg4OTMzNjI3fQ.9uH0_i_LVyuUNy1kWmLbCZ0rSndOsIKHzLGh1lwk7Uo"
}
payload = {
    "dispatch_type": "STANDARD",
    "warehouse_ids": [2],
    "items": [{"product_id": 1, "quantity": 1}]
}

response = requests.post(url, json=payload, headers=headers)
print(f"Status: {response.status_code}")
print(response.text)
