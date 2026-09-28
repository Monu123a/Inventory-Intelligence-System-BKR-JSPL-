import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Inventory

db = SessionLocal()
inv = Inventory(company_id=2, warehouse_id=39, product_id=1, available_qty=100)
db.add(inv)
db.commit()
print("Stock mocked")
