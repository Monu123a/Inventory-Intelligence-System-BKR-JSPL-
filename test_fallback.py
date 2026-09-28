import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse

db = SessionLocal()
whs = db.query(Warehouse).all()
centrals = [w for w in whs if w.warehouse_type == 'CENTRAL']
for w in centrals:
    print(w.id, w.name, w.code, w.company_id)
