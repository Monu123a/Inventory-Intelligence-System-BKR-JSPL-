import pytest
from app.models.db import SessionLocal
from app.models.schema import Company, User, Warehouse, StateHub, Product, Inventory, CompanySettings, FCDispatch, Sale
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem

@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    yield db
    db.close()

def test_central_to_fc_dispatch_xml_off(db):
    company = db.query(Company).first()
    if not company:
        pytest.skip("No company found")
        
    user = db.query(User).first()
    
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company.id).first()
    if not settings:
        settings = CompanySettings(company_id=company.id)
        db.add(settings)
    
    settings.export_internal_distribution_to_accounting = False
    db.commit()
    
    central_wh = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.warehouse_type == "CENTRAL").first()
    if not central_wh:
        pytest.skip("Central Warehouse not found")
        
    fc = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.warehouse_type == "FULFILLMENT_CENTER").first()
    if not fc:
        pytest.skip("FC Warehouse not found")
        
    product = db.query(Product).filter(Product.company_id == company.id).first()
    
    # Add dummy inventory
    inv = db.query(Inventory).filter(Inventory.company_id == company.id, Inventory.warehouse_id == central_wh.id, Inventory.product_id == product.id).first()
    if not inv:
        inv = Inventory(company_id=company.id, warehouse_id=central_wh.id, product_id=product.id, current_qty=100, available_qty=100, reserved_qty=0)
        db.add(inv)
    else:
        inv.current_qty += 100
        inv.available_qty += 100
    db.commit()
    
    req = FCDispatchBatchRequest(
        source_type="CENTRAL_WAREHOUSE",
        warehouse_ids=[fc.id],
        items=[FCDispatchRequestItem(product_id=product.id, quantity=1)]
    )
    
    dispatches = FCDispatchService.create_batch_dispatch(db, company.id, req, user.id)
    assert len(dispatches) == 1
    
    dispatch = dispatches[0]
    assert dispatch.source_warehouse_id == central_wh.id
    
    # Verify XML skipped
    sale = db.query(Sale).filter(Sale.id == dispatch.invoice_id).first()
    assert sale.tally_sync_status == "SKIPPED"
    assert dispatch.dispatch_status == "Completed"

def test_central_to_fc_dispatch_xml_on(db):
    company = db.query(Company).first()
    if not company:
        pytest.skip("No company found")
        
    user = db.query(User).first()
    
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company.id).first()
    settings.export_internal_distribution_to_accounting = True
    db.commit()
    
    central_wh = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.warehouse_type == "CENTRAL").first()
    if not central_wh:
        pytest.skip("Central Warehouse not found")
        
    fc = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.warehouse_type == "FULFILLMENT_CENTER").first()
    
    product = db.query(Product).filter(Product.company_id == company.id).first()
    
    req = FCDispatchBatchRequest(
        source_type="CENTRAL_WAREHOUSE",
        warehouse_ids=[fc.id],
        items=[FCDispatchRequestItem(product_id=product.id, quantity=1)]
    )
    
    dispatches = FCDispatchService.create_batch_dispatch(db, company.id, req, user.id)
    assert len(dispatches) == 1
    
    dispatch = dispatches[0]
    
    sale = db.query(Sale).filter(Sale.id == dispatch.invoice_id).first()
    assert sale.tally_sync_status == "PENDING"
    assert dispatch.dispatch_status == "XML Pending"
