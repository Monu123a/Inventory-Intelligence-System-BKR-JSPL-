import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_user, get_current_company_id
from app.models.schema import User, Warehouse, Product, Inventory
from app.models.db import SessionLocal

db = SessionLocal()

app.dependency_overrides[get_current_user] = lambda: User(id=1, role="Admin")
app.dependency_overrides[get_current_company_id] = lambda: 2

src_wh = db.query(Warehouse).filter(Warehouse.company_id == 2, Warehouse.warehouse_type == 'CENTRAL').first()
if not src_wh:
    src_wh = db.query(Warehouse).filter(Warehouse.company_id == 2).first()

inv = db.query(Inventory).filter(Inventory.company_id == 2, Inventory.warehouse_id == src_wh.id, Inventory.product_id == 1).first()
if not inv:
    inv = Inventory(company_id=2, warehouse_id=src_wh.id, product_id=1, current_qty=100, available_qty=100)
    db.add(inv)
else:
    inv.available_qty = 100
db.commit()

dest_wh = db.query(Warehouse).filter(Warehouse.company_id != 2).first()

client = TestClient(app)

payload = {
    "dispatch_type": "STANDARD",
    "warehouse_ids": [dest_wh.id],
    "items": [{"product_id": 1, "quantity": 1}]
}

response = client.post("/api/fc-dispatches/", json=payload)
print(response.status_code)
import json
print(json.dumps(response.json(), indent=2))
