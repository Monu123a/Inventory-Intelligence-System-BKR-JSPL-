import time
import requests

url = "https://inventory-intelligence-system-bkr-jspl-90e6.onrender.com/api/fc-dispatches/debug-log"

print("Polling...")
for i in range(15):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            if "Could not read log" not in r.text and r.text.strip():
                print(r.text)
                break
            else:
                print(f"[{i}] Still missing or empty:", r.text.strip())
        else:
            print(f"[{i}] Status:", r.status_code)
    except Exception as e:
        print("Error:", e)
    time.sleep(10)
