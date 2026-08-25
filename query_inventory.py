import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from sqlalchemy import func
from app.models.schema import Inventory, Warehouse

db = SessionLocal()
def print_inv(wh_id):
    total = db.query(func.sum(Inventory.current_qty)).filter(Inventory.warehouse_id == wh_id).scalar()
    wh = db.query(Warehouse).filter(Warehouse.id == wh_id).first()
    print(f"Warehouse {wh.name} (ID {wh_id}, Code {wh.code}) has total inventory: {total}")

print_inv(1)
print_inv(39)

