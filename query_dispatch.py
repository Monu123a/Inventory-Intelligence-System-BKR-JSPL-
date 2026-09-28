import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import FCDispatch, Warehouse, Company

db = SessionLocal()
d = db.query(FCDispatch).filter(FCDispatch.dispatch_number == "WHT/CHANDIGARH/26-27/00003").first()
if d:
    src = db.query(Warehouse).filter(Warehouse.id == d.source_warehouse_id).first()
    dst = db.query(Warehouse).filter(Warehouse.id == d.warehouse_id).first()
    print(f"Company ID: {d.company_id}")
    print(f"Source: {src.name} (ID: {src.id}, Company: {src.company_id})")
    print(f"Dest: {dst.name} (ID: {dst.id}, Company: {dst.company_id})")
else:
    print("Dispatch not found")
