import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse
db = SessionLocal()
w = db.query(Warehouse).filter(Warehouse.id == 3).first()
print(f"ID: {w.id}, Name: {w.name}, Code: {w.code}, Type: {w.warehouse_type}")
