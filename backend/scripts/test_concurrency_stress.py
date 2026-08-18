import os
import sys
import threading
from pathlib import Path
from sqlalchemy.orm import Session
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import uuid

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.db import SessionLocal
from app.models.schema import Company, User, Warehouse, Product, Inventory, FCDispatch, FCDispatchItem, CompanyUser, StateHub, InventoryMovement
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.services.inventory_event_engine import InventoryEventEngine

def setup_test_data():
    db = SessionLocal()
    company = Company(name="Concurrency Test Co", code="CTEST")
    db.add(company)
    db.flush()
    
    user = User(username="test_ct", password_hash="hash", role="ADMIN")
    db.add(user)
    db.flush()

    company_user = CompanyUser(user_id=user.id, company_id=company.id)
    db.add(company_user)
    
    hub = StateHub(hub_code="CTEST-HUB", hub_name="Test Hub", company_id=company.id)
    db.add(hub)
    db.flush()

    wh1 = Warehouse(name="WH1", code="BKR", company_id=company.id, hub_id=hub.id)
    wh2 = Warehouse(name="WH2", code="WH2", company_id=company.id, hub_id=hub.id)
    db.add_all([wh1, wh2])
    db.flush()
    
    prod = Product(name="Concurrent Item", sku="CT-001", company_id=company.id)
    db.add(prod)
    db.flush()
    
    inv = Inventory(warehouse_id=wh1.id, product_id=prod.id, company_id=company.id)
    db.add(inv)
    db.flush()
    
    InventoryEventEngine.process_event(
        db=db,
        company_id=company.id,
        product_sku=prod.sku,
        warehouse_id=wh1.id,
        quantity=20,
        event_type="ADD",
        source="SYSTEM",
        reference_id="TEST-INIT",
        user_id=user.id
    )
    db.commit()
    
    data = {
        "company_id": company.id,
        "user_id": user.id,
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "prod_id": prod.id,
        "inv_id": inv.id
    }
    db.close()
    return data

def concurrent_dispatch(data, worker_id, results):
    # Each thread needs its own DB session
    
    db = SessionLocal()
    try:
        req = FCDispatchBatchRequest(
            source_warehouse_id=data["wh1_id"],
            warehouse_ids=[data["wh2_id"]],
            dispatch_type="STANDARD",
            items=[FCDispatchRequestItem(product_id=data["prod_id"], quantity=5)]
        )
        
        FCDispatchService.create_batch_dispatch(db, data["company_id"], req, data["user_id"])
        db.commit()
        results.append((worker_id, "SUCCESS"))
        db.close()
        return
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        db.close()
        results.append((worker_id, f"FAILED: {e}"))
        return

def test_concurrency_stress():
    print("Setting up concurrency test data...")
    data = setup_test_data()
    
    # We have 20 units in stock.
    # We will launch 5 threads, each trying to dispatch 5 units.
    # Total requested = 25 units.
    # Since 25 > 20, at least ONE thread MUST fail.
    # 4 threads should succeed (4 * 5 = 20), 1 should fail.
    # If the system does not properly lock rows, all 5 might succeed leading to negative stock!
    
    results = []
    print("Launching 5 concurrent dispatch requests...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(5):
            executor.submit(concurrent_dispatch, data, i, results)
            
    print("Results:")
    successes = 0
    failures = 0
    for r in results:
        print(f"Worker {r[0]}: {r[1]}")
        if r[1] == "SUCCESS":
            successes += 1
        else:
            failures += 1
            
    print(f"Total Successes: {successes} (Expected: 4)")
    print(f"Total Failures: {failures} (Expected: 1)")
    
    db = SessionLocal()
    try:
        final_inv = db.query(Inventory).filter(Inventory.id == data["inv_id"]).first()
        print(f"Final Inventory Available Qty: {final_inv.available_qty} (Expected: 0)")
        
        assert successes == 4, f"Race condition detected! Expected 4 successes, got {successes}"
        assert failures == 1, f"Expected 1 failure, got {failures}"
        
        # Verify Inventory NEVER negative
        assert final_inv.available_qty == 0, f"Negative stock detected! Qty: {final_inv.available_qty}"
        assert final_inv.current_qty == 0, f"Ghost stock detected! Qty: {final_inv.current_qty}"
        
        # Verify no deadlocks/lock timeouts
        for r in results:
            if r[1] != "SUCCESS":
                assert "Insufficient" in r[1] or "ValueError" in r[1] or "Max Retries" in r[1], f"Unexpected error (possible deadlock/timeout): {r[1]}"
                
        # Verify no partial commits and no duplicate rows
        dispatch_count = db.query(FCDispatch).filter(FCDispatch.company_id == data["company_id"]).count()
        assert dispatch_count == successes, f"Expected {successes} FCDispatches, found {dispatch_count}. Partial commit or duplicate row!"
        
        print("✅ CONCURRENCY TEST PASSED: Row locking works properly, no deadlocks, no partial commits.")
    finally:
        # Cleanup
        try:
            db.query(FCDispatchItem).delete()
            db.query(FCDispatch).filter(FCDispatch.company_id == data["company_id"]).delete()
            db.query(Inventory).filter(Inventory.company_id == data["company_id"]).delete()
            db.query(Product).filter(Product.company_id == data["company_id"]).delete()
            db.query(Warehouse).filter(Warehouse.company_id == data["company_id"]).delete()
            db.query(StateHub).filter(StateHub.company_id == data["company_id"]).delete()
            db.query(CompanyUser).filter(CompanyUser.user_id == data["user_id"]).delete()
            db.query(User).filter(User.id == data["user_id"]).delete()
            db.query(Company).filter(Company.id == data["company_id"]).delete()
            db.commit()
        except:
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    test_concurrency_stress()
