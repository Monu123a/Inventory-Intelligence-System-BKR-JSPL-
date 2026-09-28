import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Warehouse, WarehouseType, Product

db = SessionLocal()
try:
    wh = db.query(Warehouse).filter(Warehouse.company_id == 2, Warehouse.warehouse_type == 'CENTRAL').first()
    print("Warehouse type query successful:", wh)
    
    whs = db.query(Warehouse).filter_by(company_id=2, status="ACTIVE").all()
    print("Warehouse status query successful:", len(whs))
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
