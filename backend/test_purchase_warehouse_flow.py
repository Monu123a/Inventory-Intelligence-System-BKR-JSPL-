import os
import sys
import uuid
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db import get_db
from app.models.schema import Company, User, Warehouse, Product, Inventory, InventoryMovement, Purchase, PurchaseItem
from app.services.purchase_service import PurchaseService, PurchaseDraftRequest, PurchaseItemRequest, PurchaseReceiveRequest

from dotenv import load_dotenv
load_dotenv('backend/.env')
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionTest = sessionmaker(bind=engine)

def run_test():
    db = SessionTest()
    try:
        # Use company 3 (JSPL) for testing
        company = db.query(Company).filter_by(id=3).first()
        if not company:
            company = db.query(Company).first()
        operator = db.query(User).first()
        
        # Pick warehouse 14 (Central)
        target_wh = db.query(Warehouse).filter_by(company_id=company.id, id=14).first()
        if not target_wh:
            target_wh = db.query(Warehouse).filter_by(company_id=company.id).first()
            
        print(f"Testing with Company: {company.name} (ID: {company.id}), Warehouse: {target_wh.name} (ID: {target_wh.id})")
        
        # Pick or create a test SKU
        test_sku = "TEST" + str(uuid.uuid4())[:6].upper()
        test_qty = 5
        
        # Check initial inventory in target warehouse and other warehouses
        print(f"Creating product {test_sku}...")
        prod = Product(
            company_id=company.id,
            sku=test_sku,
            name="Test Purchase Product",
            item_rate=250.0,
            default_gst_rate=18.0,
            status="Active"
        )
        db.add(prod)
        db.flush()
        
        inv_before = db.query(Inventory).filter_by(company_id=company.id, product_id=prod.id, warehouse_id=target_wh.id).first()
        qty_before = inv_before.current_qty if inv_before else 0
        print(f"Initial inventory for {test_sku} in warehouse {target_wh.id}: {qty_before}")

        # 1. Create Purchase Draft
        draft_key = str(uuid.uuid4())
        test_inv_num = "TEST-PUR-" + str(uuid.uuid4())[:6]
        draft_req = PurchaseDraftRequest(
            idempotency_key=draft_key,
            company_id=company.id,
            vendor_name="Warehouse Verification Vendor",
            invoice_number=test_inv_num,
            warehouse_id=target_wh.id,
            items=[
                PurchaseItemRequest(
                    product_sku=test_sku,
                    description="Test Purchase Item",
                    qty=test_qty,
                    unit_cost=250.0,
                    gst_pct=18.0
                )
            ]
        )
        
        draft_res = PurchaseService.create_draft(db, draft_req, operator.id)
        purchase_id = draft_res["id"]
        print(f"Draft created with ID: {purchase_id}")
        
        # Verify purchase record has warehouse_id
        purchase = db.query(Purchase).filter_by(id=purchase_id).first()
        assert purchase.warehouse_id == target_wh.id, f"Expected purchase.warehouse_id={target_wh.id}, got {purchase.warehouse_id}"
        assert purchase.status == "DRAFT"
        print("✓ Purchase draft correctly stored the selected warehouse_id!")
        
        # Verify inventory has NOT changed yet (still in draft)
        inv_during_draft = db.query(Inventory).filter_by(company_id=company.id, product_id=prod.id, warehouse_id=target_wh.id).first()
        qty_during_draft = inv_during_draft.current_qty if inv_during_draft else 0
        assert qty_during_draft == qty_before, f"Inventory should not change on draft! Before: {qty_before}, Now: {qty_during_draft}"
        print("✓ Inventory was NOT touched during draft creation.")
        
        # 2. Receive the purchase stock
        receive_key = str(uuid.uuid4())
        recv_req = PurchaseReceiveRequest(
            idempotency_key=receive_key,
            warehouse_id=target_wh.id
        )
        
        recv_res = PurchaseService.receive_purchase(db, purchase_id, recv_req, operator.id)
        print(f"Receive result: {recv_res}")
        
        # Verify inventory in target warehouse
        inv_after = db.query(Inventory).filter_by(company_id=company.id, product_id=prod.id, warehouse_id=target_wh.id).first()
        assert inv_after is not None, "Inventory record should exist in target warehouse"
        expected_qty = qty_before + test_qty
        assert inv_after.current_qty == expected_qty, f"Expected qty {expected_qty}, got {inv_after.current_qty}"
        print(f"✓ Inventory in target warehouse {target_wh.name} correctly increased from {qty_before} to {inv_after.current_qty} (+{test_qty})!")
        
        # Verify NO other warehouse has inventory for this SKU
        other_inventories = db.query(Inventory).filter(
            Inventory.company_id == company.id,
            Inventory.product_id == prod.id,
            Inventory.warehouse_id != target_wh.id
        ).all()
        for other_inv in other_inventories:
            assert other_inv.current_qty == 0, f"Other warehouse {other_inv.warehouse_id} should not have stock! Got {other_inv.current_qty}"
        print("✓ Verified: NO OTHER warehouse inventory was modified! Stock was added ONLY to the selected warehouse.")
        
        # Verify InventoryMovement record
        mov = db.query(InventoryMovement).filter_by(source="PURCHASE", reference_id=test_inv_num).first()
        assert mov is not None, "Inventory movement record must exist"
        assert mov.warehouse_id == target_wh.id, f"Movement warehouse should be {target_wh.id}, got {mov.warehouse_id}"
        assert mov.qty_changed == test_qty, f"Movement qty_changed should be {test_qty}, got {mov.qty_changed}"
        print(f"✓ Inventory movement recorded with warehouse_id={mov.warehouse_id} and qty_changed=+{mov.qty_changed}")
        
        # 3. Test Receive without specifying warehouse_id in request (verifying fallback to purchase.warehouse_id)
        # Create a second test draft
        draft_key_2 = str(uuid.uuid4())
        test_inv_num_2 = "TEST-PUR-" + str(uuid.uuid4())[:6]
        draft_req_2 = PurchaseDraftRequest(
            idempotency_key=draft_key_2,
            company_id=company.id,
            vendor_name="Warehouse Verification Vendor",
            invoice_number=test_inv_num_2,
            warehouse_id=target_wh.id,
            items=[
                PurchaseItemRequest(
                    product_sku=test_sku,
                    description="Test Purchase Item 2",
                    qty=3,
                    unit_cost=250.0,
                    gst_pct=18.0
                )
            ]
        )
        draft_res_2 = PurchaseService.create_draft(db, draft_req_2, operator.id)
        purchase_id_2 = draft_res_2["id"]
        
        # Receive WITHOUT passing warehouse_id (e.g. from modal or API defaulting to purchase.warehouse_id)
        recv_req_2 = PurchaseReceiveRequest(
            idempotency_key=str(uuid.uuid4()),
            warehouse_id=None # should use purchase.warehouse_id
        )
        PurchaseService.receive_purchase(db, purchase_id_2, recv_req_2, operator.id)
        
        inv_after_2 = db.query(Inventory).filter_by(company_id=company.id, product_id=prod.id, warehouse_id=target_wh.id).first()
        assert inv_after_2.current_qty == expected_qty + 3, f"Expected {expected_qty + 3}, got {inv_after_2.current_qty}"
        print(f"✓ Receive without warehouse_id in payload properly used purchase.warehouse_id={target_wh.id} (+3 units -> {inv_after_2.current_qty})")

        print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        print("Test failed with error:", e)
        raise
    finally:
        # Roll back all test records safely so test doesn't pollute live data
        db.rollback()
        db.close()
        print("Cleanly rolled back test transaction. Live data remains untouched.")

if __name__ == "__main__":
    run_test()
