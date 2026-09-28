import sys
import os
import json
sys.path.append('.')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import *
from app.api.routers.pos import update_sale, PosCheckoutRequest, PosCartItem
from pydantic import ValidationError

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

payload = PosCheckoutRequest(
    invoice_type="B2C",
    total_taxable_amount=100.0,
    total_tax=0.0,
    grand_total=100.0,
    payment_method="Cash",
    origin_warehouse_id=2,
    items=[
        PosCartItem(
            product_id=2132,
            sku="HM0433",
            quantity=1,
            selling_price=100.0,
            gst_rate=5.0,
            taxable_amount=100.0,
            cgst=0,
            sgst=0,
            line_total=100.0
        )
    ]
)

class DummyUser:
    id = 1

try:
    res = update_sale(sale_id=50, payload=payload, company_id=2, db=db, user=DummyUser())
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
