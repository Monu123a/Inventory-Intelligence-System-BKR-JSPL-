import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.models.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE sales DROP COLUMN shipping_name;"))
    db.execute(text("ALTER TABLE sales DROP COLUMN shipping_address;"))
    db.execute(text("ALTER TABLE sales DROP COLUMN shipping_state;"))
    db.execute(text("ALTER TABLE sales DROP COLUMN shipping_state_code;"))
    db.execute(text("ALTER TABLE sales DROP COLUMN shipping_gstin;"))
    db.commit()
    print("Columns dropped successfully.")
except Exception as e:
    db.rollback()
    print("Error:", e)
