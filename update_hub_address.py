import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import StateHub, Warehouse

db = SessionLocal()

hubs = db.query(StateHub).all()

for hub in hubs:
    fcs = db.query(Warehouse).filter(Warehouse.hub_id == hub.id).all()
    if not fcs:
        continue
        
    print(f"Hub: {hub.hub_name} ({hub.hub_code}) - Current Address: {hub.address}")
    
    new_lines = []
    # If the hub already has an address, we can keep it as the first line, OR we just replace it?
    # "take all codes address and add this all in statehub adress all in different lines"
    # Let's see what the current address is.
