import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import StateHub, Warehouse

db = SessionLocal()
hubs = db.query(StateHub).all()

updated_count = 0

for hub in hubs:
    fcs = db.query(Warehouse).filter(Warehouse.hub_id == hub.id, Warehouse.address != None, Warehouse.address != "").all()
    if fcs:
        lines = []
        for fc in fcs:
            lines.append(f"{fc.code} - {fc.address}")
        
        hub_address = "\n".join(lines)
        hub.address = hub_address
        updated_count += 1
        print(f"Updated {hub.hub_name}:\n{hub_address}\n")

db.commit()
print(f"Successfully updated {updated_count} Hubs.")
