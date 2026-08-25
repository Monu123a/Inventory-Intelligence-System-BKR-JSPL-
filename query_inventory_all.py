import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from sqlalchemy import func
from app.models.schema import Inventory, Warehouse

db = SessionLocal()
res = db.query(Warehouse.id, Warehouse.name, Warehouse.code, func.sum(Inventory.current_qty)).join(Inventory, Inventory.warehouse_id == Warehouse.id).filter(Warehouse.company_id == 2).group_by(Warehouse.id).all()
for r in res:
    print(r)

# Check company ID 2 (is BKR?)
from app.models.schema import Company
comp = db.query(Company).filter(Company.code == 'BKR').first()
print("BKR Company ID:", comp.id)

res2 = db.query(Warehouse.id, Warehouse.name, Warehouse.code, func.sum(Inventory.current_qty)).join(Inventory, Inventory.warehouse_id == Warehouse.id).filter(Warehouse.company_id == comp.id).group_by(Warehouse.id).all()
for r in res2:
    print("BKR Inv:", r)

res_jspl = db.query(Warehouse.id, Warehouse.name, Warehouse.code, func.sum(Inventory.current_qty)).join(Inventory, Inventory.warehouse_id == Warehouse.id).filter(Warehouse.company_id == 1).group_by(Warehouse.id).all()
for r in res_jspl:
    print("JSPL Inv:", r)

