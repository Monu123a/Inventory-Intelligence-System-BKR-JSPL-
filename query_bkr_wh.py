import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse

db = SessionLocal()
whs = db.query(Warehouse).filter(Warehouse.company_id == 2).all()
for w in whs:
    print(w.id, w.name, w.code, w.warehouse_type)
