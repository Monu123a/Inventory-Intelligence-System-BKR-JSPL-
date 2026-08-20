from fastapi.testclient import TestClient
from app.main import app
from app.models.db import SessionLocal
from app.models.schema import User, Company, Warehouse, Product, Inventory
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem

def test_fc_dispatch_with_edits():
    db = SessionLocal()
    
    company = db.query(Company).filter_by(code="JSPL").first()
    if not company:
        print("Company JSPL not found")
        db.close()
        return
        
    user = db.query(User).first()
    if not user:
        print("User not found")
        db.close()
        return

    # Find VSHB
    vshb = db.query(Warehouse).filter_by(company_id=company.id, code="VSHB").first()
    dest = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.code != "VSHB").first()
    
    if not vshb or not dest:
        print("Warehouses not found")
        db.close()
        return

    inventory = db.query(Inventory).filter(Inventory.warehouse_id == vshb.id, Inventory.available_qty > 0).first()
    if not inventory:
        print("Inventory not found")
        db.close()
        return
        
    req = FCDispatchBatchRequest(
        dispatch_type="STANDARD",
        source_warehouse_id=vshb.id,
        warehouse_ids=[dest.id],
        hub_id=dest.hub_id,
        items=[
            FCDispatchRequestItem(
                product_id=inventory.product_id,
                quantity=1,
                edited_selling_price=999.99,
                edited_gst_percent=12.0
            )
        ],
        edited_invoice_number="EDITED-INV-001",
        edited_invoice_date="2026-08-20T00:00:00Z",
        edited_notes="Test edited notes"
    )

    try:
        dispatches = FCDispatchService.create_batch_dispatch(db, company.id, req, user.id)
        assert len(dispatches) == 1
        d = dispatches[0]
        
        # Verify payload persisted
        assert d.payload is not None
        assert d.payload["edited_invoice_number"] == "EDITED-INV-001"
        assert d.payload["items"][0]["edited_selling_price"] == 999.99
        
        # Verify invoice used the edits
        invoice = d.invoice
        assert invoice is not None
        assert invoice.invoice_number == "EDITED-INV-001"
        assert invoice.delivery_note == "Test edited notes"
        
        item = invoice.items[0]
        assert item.selling_price == 999.99
        assert item.gst_rate == 12.0
        
        print("Test passed: Edited values persisted correctly in Transfer, Invoice, and Items!")
        
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    test_fc_dispatch_with_edits()
