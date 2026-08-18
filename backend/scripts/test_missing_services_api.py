from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_missing_services():
    headers = {"X-Company-Id": "3"}
    
    # 1. Test Delivery Challan (Invalid Create)
    print("--- Delivery Challans ---")
    payload = {"challan_number": "DC-TEST"}
    r = client.post("/api/delivery-challans/", json=payload, headers=headers)
    print(f"POST /api/delivery-challans/ (401/400/422): {r.status_code} - {r.json()}")

    # 2. Test Amazon Returns (Inspect Invalid)
    print("\n--- Amazon Returns ---")
    payload = {"decision": "INVALID", "notes": "Test"}
    r = client.post("/api/amazon-returns/999/inspect", json=payload, headers=headers)
    print(f"POST /api/amazon-returns/999/inspect (401/400/422/404): {r.status_code} - {r.json()}")

    # 3. Test Damage Claims (Create Invalid)
    print("\n--- Damage Claims ---")
    payload = {"product_id": 999, "quantity": 10, "reason": "Test", "warehouse_id": 1}
    r = client.post("/api/damage-claims/", json=payload, headers=headers)
    print(f"POST /api/damage-claims/ (401/400/422/404): {r.status_code} - {r.json()}")

if __name__ == "__main__":
    test_missing_services()
