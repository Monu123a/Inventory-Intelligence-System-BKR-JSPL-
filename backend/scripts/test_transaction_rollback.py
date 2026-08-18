import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.db import SessionLocal
from app.models.schema import Company, User, Warehouse, Product, Inventory, FCDispatch, FCDispatchItem, CompanyUser, StateHub
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.services.inventory_event_engine import InventoryEventEngine
import pytest

def setup_test_data(db: Session):
    # Create company, user, warehouses, product, and inventory
    company = Company(name="Rollback Test Co", code="RBTEST")
    db.add(company)
    db.flush()
    
    user = User(username="test_rb", password_hash="hash", role="ADMIN")
    db.add(user)
    db.flush()

    company_user = CompanyUser(user_id=user.id, company_id=company.id)
    db.add(company_user)
    
    hub = StateHub(hub_code="TEST-HUB", hub_name="Test Hub", company_id=company.id)
    db.add(hub)
    db.flush()

    wh1 = Warehouse(name="WH1", code="BKR", company_id=company.id, hub_id=hub.id)
    wh2 = Warehouse(name="WH2", code="WH2", company_id=company.id, hub_id=hub.id)
    db.add_all([wh1, wh2])
    db.flush()
    
    prod = Product(name="Rollback Item", sku="RB-001", company_id=company.id)
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
        quantity=10,
        event_type="ADD",
        source="SYSTEM",
        reference_id="TEST-INIT",
        user_id=user.id
    )
    db.commit()
    
    return company, user, wh1, wh2, prod, inv

def test_rollback_on_failure():
    db = SessionLocal()
    try:
        data = setup_test_data(db)
        company, user, wh1, wh2, prod, inv = data
        
        # Scenario: We want to dispatch 15 items, but we only have 10.
        # This should fail inside the InventoryEventEngine and raise ValueError.
        req = FCDispatchBatchRequest(
            source_warehouse_id=wh1.id,
            warehouse_ids=[wh2.id],
            dispatch_type="STANDARD",
            items=[FCDispatchRequestItem(product_id=prod.id, quantity=15)]
        )
        
        try:
            # We wrap this in a transaction block exactly like the router does
            dispatches = FCDispatchService.create_batch_dispatch(db, company.id, req, user.id)
            db.commit()
            print("❌ FAILURE: Dispatch succeeded unexpectedly!")
        except Exception as e:
            db.rollback()
            print(f"✅ SUCCESS: Caught expected error: {e}")
            
        # Verify rollback
        # 1. No FCDispatch records should exist for this company
        dispatch_count = db.query(FCDispatch).filter(FCDispatch.company_id == company.id).count()
        assert dispatch_count == 0, f"Expected 0 dispatches, found {dispatch_count}"
        
        # 2. Inventory should be completely unchanged (10)
        final_inv = db.query(Inventory).filter(Inventory.id == inv.id).first()
        assert final_inv.available_qty == 10, f"Expected 10 qty, found {final_inv.available_qty}"
        
        print("✅ ROLLBACK VERIFIED: Parent records, child records, and inventory remain clean.")
        
    finally:
        # Cleanup
        try:
            db.query(FCDispatchItem).delete()
            db.query(FCDispatch).filter(FCDispatch.company_id == company.id).delete()
            db.query(Inventory).filter(Inventory.company_id == company.id).delete()
            db.query(Product).filter(Product.company_id == company.id).delete()
            db.query(Warehouse).filter(Warehouse.company_id == company.id).delete()
            db.query(StateHub).filter(StateHub.company_id == company.id).delete()
            db.query(CompanyUser).filter(CompanyUser.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
            db.query(Company).filter(Company.id == company.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    test_rollback_on_failure()
