import os
import requests
import uuid
import threading

API_BASE = "http://localhost:8000"
TOKEN = os.getenv("AUTH_TOKEN", "dummy_token_if_auth_bypassed")

def run_tests():
    print("--- Running UAT Cross-Company Transfers ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}

    # For the sake of this script, we assume Companies 1 and 2 exist, 
    # and warehouses 1 (in Company 1) and 2 (in Company 2) exist.
    # In a real staging environment with test fixtures, we'd create them via API.
    
    source_company_id = 1
    dest_company_id = 2
    source_warehouse_id = 1
    dest_warehouse_id = 2
    
    # 1. Attempt transfer where SKU missing in destination
    print("\n[Test 1] Missing SKU in Destination")
    payload_missing = {
        "idempotency_key": str(uuid.uuid4()),
        "source_company_id": source_company_id,
        "destination_company_id": dest_company_id,
        "source_warehouse_id": source_warehouse_id,
        "destination_warehouse_id": dest_warehouse_id,
        "items": [
            {"product_sku": "MISSING_SKU_999", "quantity": 1}
        ]
    }
    
    resp = requests.post(f"{API_BASE}/api/transfers/create", json=payload_missing, headers=headers)
    print(f"Missing SKU response status: {resp.status_code}")
    # We expect 400 with missing_skus
    if resp.status_code == 400 and "missing_skus" in resp.text:
        print("✅ Correctly rejected missing SKU")
    else:
        print(f"❌ Failed to reject missing SKU. Response: {resp.text}")

    # 2. Idempotent Concurrent Requests
    print("\n[Test 2] Concurrent Completions with same Idempotency Key")
    # For this we assume SKU 'TEST_SKU_1' exists in both and has inventory in source
    idem_key = str(uuid.uuid4())
    payload_concurrent = {
        "idempotency_key": idem_key,
        "source_company_id": source_company_id,
        "destination_company_id": dest_company_id,
        "source_warehouse_id": source_warehouse_id,
        "destination_warehouse_id": dest_warehouse_id,
        "items": [
            {"product_sku": "TEST_SKU_1", "quantity": 1}
        ]
    }

    results = []
    def fire_request():
        r = requests.post(f"{API_BASE}/api/transfers/create", json=payload_concurrent, headers=headers)
        results.append(r.status_code)

    t1 = threading.Thread(target=fire_request)
    t2 = threading.Thread(target=fire_request)
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    print(f"Concurrent responses: {results}")
    if 200 in results and 201 in results:
         # One might be 201 (Created), one 200 (Idempotent OK)
         print("✅ Idempotency logic handled concurrency successfully.")
    
    # Check DB movements
    # Since we don't have direct DB access here, we output the verification instructions
    print("\n--- Next Steps for Verification ---")
    print("Run these queries on the database:")
    print("1. SELECT COUNT(*) FROM inventory_movements WHERE idempotency_key = '{}';".format(idem_key))
    print("   -> Expect EXACTLY 2 rows (1 OUT, 1 IN).")
    print("2. SELECT * FROM inventory_movements WHERE company_id = {} AND movement_type = 'OUT';".format(source_company_id))
    print("   -> Expect EXACTLY 1 row for this transfer.")
    print("3. SELECT * FROM inventory_movements WHERE company_id = {} AND movement_type = 'IN';".format(dest_company_id))
    print("   -> Expect EXACTLY 1 row for this transfer.")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"Could not connect to API or run tests fully. {e}")
