from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_warehouse_api():
    headers = {"X-Company-Id": "3"}
    
    # 1. State Hubs
    print("\n--- State Hubs ---")
    r = client.post("/api/state-hubs/", json={"hub_name": "Test Hub", "hub_code": "TH"}, headers=headers)
    print(f"POST /api/state-hubs/ (401/400/422): {r.status_code} - {r.json()}")

    # 2. Warehouses
    print("\n--- Warehouses ---")
    r = client.post("/api/warehouses/", json={"name": "Test WH", "code": "WH", "warehouse_type": "FULFILLMENT_CENTER", "status": "ACTIVE"}, headers=headers)
    print(f"POST /api/warehouses/ (401/400/422): {r.status_code} - {r.json()}")

    r = client.get("/api/warehouses/999/users", headers=headers)
    print(f"GET /api/warehouses/999/users (401/404): {r.status_code} - {r.json()}")

    # 3. Warehouse Inventory
    print("\n--- Warehouse Inventory ---")
    r = client.get("/api/warehouse-inventory/", headers=headers)
    print(f"GET /api/warehouse-inventory/ (401/200): {r.status_code}")

if __name__ == "__main__":
    test_warehouse_api()
