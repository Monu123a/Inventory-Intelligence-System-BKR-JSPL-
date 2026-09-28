import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.models.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE sales ADD COLUMN shipping_name VARCHAR;"))
    db.execute(text("ALTER TABLE sales ADD COLUMN shipping_address TEXT;"))
    db.execute(text("ALTER TABLE sales ADD COLUMN shipping_state VARCHAR;"))
    db.execute(text("ALTER TABLE sales ADD COLUMN shipping_state_code VARCHAR;"))
    db.execute(text("ALTER TABLE sales ADD COLUMN shipping_gstin VARCHAR;"))
    db.commit()
    print("Columns added successfully.")
except Exception as e:
    db.rollback()
    print("Error:", e)
