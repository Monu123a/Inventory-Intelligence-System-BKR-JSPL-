import sys
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE sales ADD COLUMN shipping_name VARCHAR;"))
        conn.execute(text("ALTER TABLE sales ADD COLUMN shipping_address TEXT;"))
        conn.execute(text("ALTER TABLE sales ADD COLUMN shipping_state VARCHAR;"))
        conn.execute(text("ALTER TABLE sales ADD COLUMN shipping_state_code VARCHAR;"))
        conn.execute(text("ALTER TABLE sales ADD COLUMN shipping_gstin VARCHAR;"))
        conn.commit()
        print("Live DB Columns added successfully.")
    except Exception as e:
        print("Error:", e)
