import sys
import os
sys.path.append(os.getcwd())
from app.models.db import SessionLocal
from app.models.schema import Product

db = SessionLocal()
prods = db.query(Product).filter(Product.sku.like('PROD%')).all()
for p in prods:
    print(p.sku)
print(db.query(Product).count(), "total products")
