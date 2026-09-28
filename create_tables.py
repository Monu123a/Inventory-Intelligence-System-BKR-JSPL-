import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from app.models.db import engine, SessionLocal
from app.models.schema import Base
from sqlalchemy import text

print(f"Engine URL: {engine.url}")

# Create new tables
Base.metadata.create_all(engine)

# Alter existing tables
db = SessionLocal()
try:
    db.execute(text("ALTER TABLE warehouse_external_mappings ADD COLUMN amazon_network VARCHAR;"))
except Exception as e:
    print(f"Column amazon_network might already exist: {e}")

try:
    db.execute(text("ALTER TABLE company_settings ADD COLUMN amazon_sync_enabled BOOLEAN DEFAULT FALSE;"))
except Exception as e:
    print(f"Column amazon_sync_enabled might already exist: {e}")

db.commit()
db.close()
print("Database schema successfully updated!")
