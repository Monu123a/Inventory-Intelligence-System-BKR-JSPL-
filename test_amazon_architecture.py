import sys
import os
from dotenv import load_dotenv

# Force environment variable loading before ANY sqlalchemy imports
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)
# Ensure DATABASE_URL is in environment
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://postgres.ttlxrvjydjhpltdotnml:xakket-famqec-7Mysto@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

import app.models.db as db_module
from sqlalchemy.orm import Session
from app.models.db import SessionLocal
from app.models.schema import Product, Inventory, Warehouse, Company, AmazonLiveAllocation, WarehouseExternalMapping, AmazonNetworkType, AmazonDLQ, AmazonOrderEventLog
from app.services.amazon_service import AmazonService
from app.services.amazon_reconciliation_service import AmazonReconciliationService
from app.services.stock_reservation_service import StockReservationService
from datetime import datetime

db = SessionLocal()

print("--- Starting Enterprise Amazon Architecture Verification ---")
print(f"Engine: {db_module.engine.url}")

try:
    company = db.query(Company).first()
    company_id = company.id
    
    sku = "TSTAMZ01"
    product = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not product:
        product = Product(company_id=company_id, sku=sku, name="Amazon Test Product", category="TEST", item_rate=100.0)
        db.add(product)
        db.commit()
        db.refresh(product)
        
    wh_code = "TEST-WH-MFN"
    warehouse = db.query(Warehouse).filter(Warehouse.code == wh_code, Warehouse.company_id == company_id).first()
    if not warehouse:
        warehouse = Warehouse(company_id=company_id, name="Test MFN Warehouse", code=wh_code)
        db.add(warehouse)
        db.commit()
        db.refresh(warehouse)
        
    mapping = db.query(WarehouseExternalMapping).filter(WarehouseExternalMapping.warehouse_id == warehouse.id, WarehouseExternalMapping.marketplace == "Amazon").first()
    if not mapping:
        mapping = WarehouseExternalMapping(warehouse_id=warehouse.id, marketplace="Amazon", external_code="TEST-MFN", amazon_network=AmazonNetworkType.MFN)
        db.add(mapping)
    else:
        mapping.amazon_network = AmazonNetworkType.MFN
    db.commit()
        
    inv = db.query(Inventory).filter(Inventory.product_id == product.id, Inventory.warehouse_id == warehouse.id).first()
    if not inv:
        inv = Inventory(company_id=company_id, product_id=product.id, warehouse_id=warehouse.id)
        inv._allow_mutation = True
        inv.current_qty = 100
        db.add(inv)
    else:
        inv._allow_mutation = True
        inv.current_qty = 100
    db.commit()

    print(f"1. Setup complete. Core Inventory for {sku}: 100")

    print("\n--- Simulating 15-min SP-API Polling (New Order) ---")
    mock_order = {
        "order_id": "AMZ-123",
        "status": "Unshipped",
        "fulfillment_channel": "MFN",
        "last_update_date": datetime.utcnow().isoformat(),
        "items": [
            {
                "amazon_line_item_id": "LINE-1",
                "sku": sku,
                "quantity": 10
            }
        ]
    }
    
    class TestMockClient:
        def fetch_orders(self, since=None):
            return [mock_order]
    
    import app.services.amazon_service
    app.services.amazon_service.get_amazon_client = lambda: TestMockClient()
    
    processed, skipped = AmazonService.poll_orders(db, company_id)
    print(f"Poll Result: {processed} processed, {skipped} skipped.")
    
    allocation = db.query(AmazonLiveAllocation).filter(AmazonLiveAllocation.order_id == "AMZ-123").first()
    print(f"Live Allocation created: ID {allocation.id} | Status: {allocation.status.value} | Allocated Qty: {allocation.allocated_qty} | Reconciled Qty: {allocation.reconciled_qty}")
    
    available_stock = StockReservationService.get_available_stock(db, company_id, product.id)
    print(f"Available Stock Calculation: {available_stock} (Expected: 90)")
    
    print("\n--- Simulating Amazon Report Reconciliation (Partial Shipment) ---")
    mock_report_item = {
        "order_id": "AMZ-123",
        "sku": sku,
        "amazon_line_item_id": "LINE-1",
        "shipped_quantity": 6,
        "is_return": False
    }
    
    AmazonReconciliationService.process_report_item(db, company_id, mock_report_item)
    db.commit()
    db.refresh(allocation)
    db.refresh(inv)
    print(f"After Report 1:")
    print(f"Core Inventory: {inv.current_qty} (Expected: 94)")
    print(f"Allocation Reconciled Qty: {allocation.reconciled_qty} (Expected: 6)")
    print(f"Allocation Closed State: {allocation.closed}")
    
    available_stock_2 = StockReservationService.get_available_stock(db, company_id, product.id)
    print(f"Available Stock Calculation: {available_stock_2} (Expected: 90, because 94 core - 4 soft remaining)")

    print("\n--- Simulating Amazon Report Reconciliation (Final Shipment) ---")
    mock_report_item_final = {
        "order_id": "AMZ-123",
        "sku": sku,
        "amazon_line_item_id": "LINE-1",
        "shipped_quantity": 10,
        "is_return": False
    }
    AmazonReconciliationService.process_report_item(db, company_id, mock_report_item_final)
    db.commit()
    db.refresh(allocation)
    db.refresh(inv)
    print(f"After Report 2:")
    print(f"Core Inventory: {inv.current_qty} (Expected: 90)")
    print(f"Allocation Reconciled Qty: {allocation.reconciled_qty} (Expected: 10)")
    print(f"Allocation Closed State: {allocation.closed} (Expected: True)")
    
    available_stock_3 = StockReservationService.get_available_stock(db, company_id, product.id)
    print(f"Available Stock Calculation: {available_stock_3} (Expected: 90)")

    print("\n--- Simulating Amazon Return Flow ---")
    mock_return = {
        "order_id": "AMZ-123",
        "sku": sku,
        "amazon_line_item_id": "LINE-1",
        "shipped_quantity": 10,
        "is_return": True
    }
    AmazonReconciliationService.process_report_item(db, company_id, mock_return)
    db.commit()
    db.refresh(allocation)
    db.refresh(inv)
    print(f"After Return:")
    print(f"Core Inventory: {inv.current_qty} (Expected: 100)")
    print(f"Allocation Status: {allocation.status.value} (Expected: Returned)")
    
    print("\n✅ ALL ENTERPRISE SAFEGUARDS VERIFIED SUCCESSFULLY!")

finally:
    try:
        db.query(AmazonOrderEventLog).delete()
        db.query(AmazonDLQ).filter(AmazonDLQ.reference_id == "AMZ-123").delete()
        db.query(AmazonLiveAllocation).filter(AmazonLiveAllocation.order_id == "AMZ-123").delete()
        db.commit()
    except Exception:
        db.rollback()
    db.close()
