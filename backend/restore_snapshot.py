import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.schema import Inventory, InventoryMovement
import sys

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("Loading snapshot...")
sys.stdout.flush()
with open('../scratch/snapshot_1233.json', 'r') as f:
    data = json.load(f)

print("Clearing tables...")
sys.stdout.flush()
db.execute(text("DELETE FROM inventory_movements"))
db.execute(text("DELETE FROM inventory"))
db.commit()

print("Restoring inventory (bulk)...")
sys.stdout.flush()
db.bulk_insert_mappings(Inventory, data['inventory'])

print("Restoring inventory_movements (bulk)...")
sys.stdout.flush()
for row in data['inventory_movements']:
    if 'metadata_payload' in row and row['metadata_payload'] is not None:
        if isinstance(row['metadata_payload'], dict):
            pass 
db.bulk_insert_mappings(InventoryMovement, data['inventory_movements'])
db.commit()
print("Snapshot 1233 restored successfully!")
sys.stdout.flush()
