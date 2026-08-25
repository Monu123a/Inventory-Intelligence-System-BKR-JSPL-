import requests
res = requests.get("https://inventory-intelligence-system-backend-c11j.onrender.com/api/pos/products/search?q=HM0038", headers={"x-company-id": "1"})
print(res.json())
