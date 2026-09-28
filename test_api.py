import requests

url = "http://localhost:8000/api/pos/sales/49"
headers = {"X-Company-Id": "2"}
res = requests.get(url, headers=headers)
print("Status Code:", res.status_code)
print("Response:", res.text)
