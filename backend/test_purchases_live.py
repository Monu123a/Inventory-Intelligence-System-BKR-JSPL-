import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
engine = create_engine(RENDER_POSTGRES_URL)
SessionTest = sessionmaker(bind=engine)

from app.models.schema import Company, User, Warehouse, Product
from app.services.purchase_service import PurchaseService, PurchaseDraftRequest, PurchaseItemRequest, PurchaseReceiveRequest

db = SessionTest()

try:
    # Get basic setup
    company = db.query(Company).first()
    operator = db.query(User).first()
    
    # 1. Test Draft Creation
    print("Testing Draft Creation...")
    draft_req = PurchaseDraftRequest(
        idempotency_key=str(uuid.uuid4()),
        company_id=company.id,
        vendor_name="Test Vendor Inc",
        invoice_number="INV-" + str(uuid.uuid4())[:6],
        items=[
            PurchaseItemRequest(
                product_sku="NEWTEST1234", 
                description="Test Inline Prod",
                qty=2,
                unit_cost=100,
                gst_pct=18
            )
        ]
    )
    
    res = PurchaseService.create_draft(db, draft_req, operator.id)
    purchase_id = res['id']
    print(f"Draft created successfully. Purchase ID: {purchase_id}")
    
    # 2. Test Idempotency Draft
    print("Testing Idempotency on Draft...")
    res2 = PurchaseService.create_draft(db, draft_req, operator.id)
    assert res2['message'] == 'Returned cached draft'
    print("Draft idempotency works!")
    
    # 3. Test Receive
    print("Testing Receive...")
    receive_key = str(uuid.uuid4())
    receive_req = PurchaseReceiveRequest(idempotency_key=receive_key)
    
    recv_res = PurchaseService.receive_purchase(db, purchase_id, receive_req, operator.id)
    print(f"Receive successful: {recv_res}")
    
    # Check Product was created
    new_prod = db.query(Product).filter_by(sku="NEWTEST1234").first()
    assert new_prod is not None
    assert new_prod.status == "DRAFT"
    print("Inline product created successfully!")
    
    # 4. Test Idempotency Receive
    print("Testing Idempotency on Receive...")
    recv_res2 = PurchaseService.receive_purchase(db, purchase_id, receive_req, operator.id)
    assert recv_res2['message'] == 'Already received'
    print("Receive idempotency works!")
    
finally:
    db.rollback()
    db.close()
    print("Rolled back test data safely.")

