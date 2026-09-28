import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import StateHub, Warehouse, Company

db = SessionLocal()
comps = db.query(Company).all()
comp_map = {c.id: c.code for c in comps}

hubs = db.query(StateHub).all()
for hub in hubs:
    fcs = db.query(Warehouse).filter(Warehouse.hub_id == hub.id).all()
    if fcs:
        print(f"\nHub: {hub.hub_name} (Code: {hub.hub_code})")
        for fc in fcs:
            print(f"  FC: {fc.name} (Company: {comp_map.get(fc.company_id, fc.company_id)})")
