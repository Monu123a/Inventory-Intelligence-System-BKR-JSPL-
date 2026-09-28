import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse

db = SessionLocal()
w = db.query(Warehouse).first()
print(repr(w.warehouse_type))
print(w.warehouse_type == "CENTRAL")
try:
    print(w.warehouse_type.name)
except Exception as e:
    print("ERROR:", e)
