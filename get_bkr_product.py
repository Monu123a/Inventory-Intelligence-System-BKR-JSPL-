import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Product, Inventory

db = SessionLocal()
inv = db.query(Inventory).filter(Inventory.company_id == 2, Inventory.warehouse_id == 39, Inventory.available_qty > 0).first()
print(f"Product ID: {inv.product_id}, SKU: {inv.product.sku}")
