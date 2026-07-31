from sqlalchemy import create_engine, text
from app.models.db import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    print(f"Connected to {DATABASE_URL}")
    tables_to_clear = [
        "stock_transfer_items",
        "stock_transfers",
        "replenishment_recommendations",
        "replenishment_runs"
    ]
    for table in tables_to_clear:
        try:
            conn.execute(text(f"DELETE FROM {table}"))
            conn.commit()
            print(f"Cleared {table}")
        except Exception as e:
            print(f"Could not clear {table}: {e}")
