import pytest
from app.models.schema import Product, Warehouse, Inventory, InventorySnapshot
from app.services.scheduler_service import midnight_inventory_snapshot

def test_midnight_snapshot(db_session, seeded_company_context):
    company = seeded_company_context["company"]

    # Setup
    wh = Warehouse(name="WH1", code="WH1", company_id=company.id)
    db_session.add(wh)
    prod = Product(sku="SKU1", name="Product 1", company_id=company.id)
    db_session.add(prod)
    db_session.flush()
    
    inv = Inventory(company_id=company.id, product_id=prod.id, warehouse_id=wh.id, current_qty=150, available_qty=150)
    db_session.add(inv)
    db_session.commit()
    
    # Execute job
    midnight_inventory_snapshot(db_session, company.id)
    
    # Verify
    snapshots = db_session.query(InventorySnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].product_id == prod.id
    assert snapshots[0].quantity == 150

# Legacy amazon test removed. The new AmazonPipeline handles its own crash recovery and idempotency via InventoryMovement.
