import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse, Company

db = SessionLocal()
warehouses = db.query(Warehouse).all()
for w in warehouses:
    comp = db.query(Company).filter(Company.id == w.company_id).first()
    print(f"ID: {w.id} | Code: {w.code} | Name: {w.name} | Type: {w.warehouse_type} | Company: {comp.name}")

