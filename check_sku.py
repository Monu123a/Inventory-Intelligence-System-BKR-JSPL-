import os
import django
import sys
sys.path.append("/Users/harshahlawat/Documents/transformation engine/backend")
from app.models.database import SessionLocal
from app.models.schema import Product

db = SessionLocal()
prods = db.query(Product).filter(Product.sku.like('PROD%')).all()
for p in prods:
    print(p.sku)

print(db.query(Product).count(), "total products")
