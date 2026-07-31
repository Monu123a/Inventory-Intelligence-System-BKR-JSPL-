import urllib.request
import json

try:
    req = urllib.request.Request("http://127.0.0.1:8000/api/companies/")
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")
