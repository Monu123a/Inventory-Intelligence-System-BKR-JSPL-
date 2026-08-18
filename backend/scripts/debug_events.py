import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.models.db import SessionLocal
from app.models.schema import InventoryMovement, Warehouse
db = SessionLocal()
wh = db.query(Warehouse).order_by(Warehouse.id.desc()).first()
print(f"Latest WH ID: {wh.id}")
events = db.query(InventoryMovement).filter(InventoryMovement.warehouse_id == wh.id).all()
print(f"Total events for WH {wh.id}: {len(events)}")
for e in events:
    print(f"Event ID {e.id}: {e.metadata_payload.get('event_type')} | qty: {e.qty_changed} | src: {e.source}")
