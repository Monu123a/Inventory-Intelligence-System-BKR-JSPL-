import sys
import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import Product

db = SessionLocal()

products = db.query(Product).filter(Product.company_id == 2).all()
found = False
for p in products:
    if "TRIMMER" in p.sku.upper():
        print(f"SKU IN DB: '{p.sku}' | len: {len(p.sku)} | Hex: {[hex(ord(c)) for c in p.sku]}")
        found = True

if not found:
    print("NO TRIMMER SKU FOUND")
