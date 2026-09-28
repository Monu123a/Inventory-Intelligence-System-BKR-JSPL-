import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse

db = SessionLocal()
whs = db.query(Warehouse).all()
for w in whs:
    if not w.warehouse_type:
        print(f"Warehouse {w.id} has no type!")
