from app.models.db import SessionLocal
from app.models.schema import Warehouse, StateHub
from sqlalchemy.orm import joinedload

db = SessionLocal()
whs = db.query(Warehouse).options(joinedload(Warehouse.hub)).all()
for w in whs:
    hub_name = w.hub.hub_name if hasattr(w, 'hub') and w.hub else "None"
    print(f"[{w.code}] {w.name} - Hub: {hub_name}")
db.close()
