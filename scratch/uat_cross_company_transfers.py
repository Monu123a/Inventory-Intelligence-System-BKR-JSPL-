import os
import requests
import uuid
import threading
import subprocess

API_BASE = "http://localhost:8000"
TOKEN = os.getenv("AUTH_TOKEN", "dummy_token")

def setup_sales():
    print("Setting up dummy invoices...")
    script = """
from app.models.db import SessionLocal
from app.models.schema import Sale, SaleItem
import uuid
db = SessionLocal()

# Create dummy invoice for missing SKU
sale1 = Sale(company_id=2, bill_number=str(uuid.uuid4()), grand_total=100.0, status='Completed', customer_name='UAT')
db.add(sale1)
db.flush()
si1 = SaleItem(sale_id=sale1.id, product_id=73, quantity=1, selling_price=100.0, sku='EXISTA')
db.add(si1)

# Create dummy invoice for valid SKU
sale2 = Sale(company_id=2, bill_number=str(uuid.uuid4()), grand_total=100.0, status='Completed', customer_name='UAT')
db.add(sale2)
db.flush()
si2 = SaleItem(sale_id=sale2.id, product_id=1155, quantity=1, selling_price=100.0, sku='EXISTA')
db.add(si2)

db.commit()
print(f'{sale1.id},{sale2.id}')
db.close()
"""
    with open("backend/temp_setup.py", "w") as f:
        f.write(script)
    result = subprocess.run(["./venv/bin/python", "temp_setup.py"], capture_output=True, text=True, cwd="backend")
    os.remove("backend/temp_setup.py")
    print(result.stdout, result.stderr); return result.stdout.strip().split(',')

def run_tests():
    print("--- Running UAT Cross-Company Transfers ---")
    headers = {"Authorization": f"Bearer {TOKEN}", "X-Company-Id": "2", "Content-Type": "application/json"}

    source_company_id = 2
    dest_company_id = 3
    source_warehouse_id = 3
    dest_warehouse_id = 14
    
    sale_missing, sale_valid = setup_sales()

    print("\n[Test 1] Missing SKU in Destination")
    idem_missing = str(uuid.uuid4())
    payload_missing = {
        "idempotency_key": idem_missing,
        "source_company_id": source_company_id,
        "destination_company_id": dest_company_id,
        "source_warehouse_id": source_warehouse_id,
        "destination_warehouse_id": dest_warehouse_id,
        "items": [
            {"product_sku": "EXISTA", "product_id": 73, "requested_qty": 1}
        ]
    }
    
    resp = requests.post(f"{API_BASE}/api/transfers/create", json=payload_missing, headers=headers)
    if resp.status_code != 200 and resp.status_code != 201:
        print(f"Failed to create transfer: {resp.text}")
        return
        
    transfer_id_missing = resp.json().get("transfer_id")
    
    comp_resp = requests.put(
        f"{API_BASE}/api/transfers/{transfer_id_missing}/complete", 
        json={"idempotency_key": idem_missing, "invoice_id": int(sale_missing)}, 
        headers=headers
    )
    print(f"Missing SKU completion status: {comp_resp.status_code}")
    if comp_resp.status_code == 400 and "missing_skus" in comp_resp.text:
        print("✅ Correctly rejected missing SKU during completion")
    else:
        print(f"❌ Failed to reject missing SKU. Response: {comp_resp.text}")

    print("\n[Test 2] Concurrent Completions")
    idem_key = str(uuid.uuid4())
    payload_valid = {
        "idempotency_key": idem_key,
        "source_company_id": source_company_id,
        "destination_company_id": dest_company_id,
        "source_warehouse_id": source_warehouse_id,
        "destination_warehouse_id": dest_warehouse_id,
        "items": [
            {"product_sku": "18980-", "product_id": 1155, "requested_qty": 1}
        ]
    }

    resp = requests.post(f"{API_BASE}/api/transfers/create", json=payload_valid, headers=headers)
    transfer_id_valid = resp.json().get("transfer_id")

    results = []
    def fire_complete():
        r = requests.put(
            f"{API_BASE}/api/transfers/{transfer_id_valid}/complete", 
            json={"idempotency_key": idem_key, "invoice_id": int(sale_valid)}, 
            headers=headers
        )
        results.append((r.status_code, r.text))

    t1 = threading.Thread(target=fire_complete)
    t2 = threading.Thread(target=fire_complete)
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    print(f"Concurrent completion responses: {[r[0] for r in results]}")
    successes = [r for r in results if r[0] == 200]
    
    if len(successes) > 0:
        print("✅ Idempotency logic handled concurrency successfully.")
    else:
        print(f"❌ Failed idempotency logic: {results}")

    print(f"\nDB Verification for Transfer ID {transfer_id_valid}:")
    print(f"SELECT COUNT(*) FROM inventory_movements WHERE transfer_id = {transfer_id_valid};")
    print(f"SELECT * FROM inventory_movements WHERE transfer_id = {transfer_id_valid} AND company_id = {source_company_id} AND movement_type = 'OUT';")
    print(f"SELECT * FROM inventory_movements WHERE transfer_id = {transfer_id_valid} AND company_id = {dest_company_id} AND movement_type = 'IN';")

if __name__ == "__main__":
    run_tests()
