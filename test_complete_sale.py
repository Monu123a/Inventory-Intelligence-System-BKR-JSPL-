import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.api.routers.pos import PosCheckoutRequest, complete_sale, PosCartItem
from app.models.schema import User, Warehouse

db = SessionLocal()
w = db.query(Warehouse).first()

req = PosCheckoutRequest(
    items=[],
    customer_name="Test",
    payment_method="CASH",
    total_taxable_amount=0,
    total_tax=0,
    grand_total=0,
    origin_warehouse_id=w.id,
    skip_inventory_update=True
)

u = db.query(User).first()
try:
    complete_sale(None, req, 2, db, u, commit=False)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
