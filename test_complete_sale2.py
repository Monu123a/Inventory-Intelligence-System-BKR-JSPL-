import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.api.routers.pos import PosCheckoutRequest, complete_sale, PosCartItem
from app.models.schema import User, Warehouse

db = SessionLocal()
w = db.query(Warehouse).first()

item = PosCartItem(
    product_id=1,
    sku="TEST",
    quantity=1,
    selling_price=100,
    gst_rate=18,
    taxable_amount=100,
    cgst=9,
    sgst=9,
    line_total=118
)

req = PosCheckoutRequest(
    items=[item],
    customer_name="Test",
    payment_method="CASH",
    total_taxable_amount=100,
    total_tax=18,
    grand_total=118,
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
