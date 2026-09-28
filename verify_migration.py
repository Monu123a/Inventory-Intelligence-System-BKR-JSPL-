import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import User, Product, Inventory

NEW_DB="postgresql://postgres.ttlxrvjydjhpltdotnml:xakket-famqec-7Mysto@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(NEW_DB)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

user_count = db.query(User).count()
product_count = db.query(Product).count()
inventory_count = db.query(Inventory).count()

print(f"Supabase Data Counts:")
print(f"Users: {user_count}")
print(f"Products: {product_count}")
print(f"Inventory Records: {inventory_count}")

db.close()
