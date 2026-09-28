import requests

base_url = "https://inventory-intelligence-system-bkr-jspl.onrender.com"
# 1. Login
login_res = requests.post(f"{base_url}/api/auth/login", data={"username": "test_admin", "password": "password"})
if login_res.status_code != 200:
    print("Login failed:", login_res.text)
    exit(1)
    
token = login_res.json()["access_token"]
print("Got token")

# 2. Trigger dispatch
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
payload = {
    "dispatch_type": "STANDARD",
    "warehouse_ids": [2],
    "items": [{"product_id": 1, "quantity": 1}]
}

print("Triggering dispatch...")
dispatch_res = requests.post(f"{base_url}/api/fc-dispatches/", json=payload, headers=headers)
print("Status:", dispatch_res.status_code)
print("Response:", dispatch_res.text)

# 3. Get debug logs
print("Fetching debug logs...")
logs_res = requests.get(f"{base_url}/api/debug/logs")
if logs_res.status_code == 200:
    logs = logs_res.json().get("logs", [])
    for line in logs[-30:]:
        print(line.strip())
else:
    print("Failed to get logs:", logs_res.text)
