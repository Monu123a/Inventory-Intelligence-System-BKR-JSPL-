import urllib.request

req = urllib.request.Request("http://127.0.0.1:8000/api/companies/")
with urllib.request.urlopen(req) as response:
    print(response.read().decode())
