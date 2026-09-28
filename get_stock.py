import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Inventory

db = SessionLocal()
invs = db.query(Inventory).filter(Inventory.company_id == 2, Inventory.warehouse_id == 39).all()
has_stock = False
for i in invs:
    if i.available_qty > 0:
        print(f"Product {i.product_id} has {i.available_qty} stock")
        has_stock = True
if not has_stock:
    print("NO STOCK AT ALL")
