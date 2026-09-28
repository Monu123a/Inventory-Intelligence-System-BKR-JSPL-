import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import StateHub, Warehouse

db = SessionLocal()
hubs = db.query(StateHub).all()
for hub in hubs:
    fcs = db.query(Warehouse).filter(Warehouse.hub_id == hub.id).all()
    if fcs:
        print(f"\nHub: {hub.hub_name}")
        for fc in fcs:
            print(f"  FC Code: {fc.code}, Address: {fc.address}")
