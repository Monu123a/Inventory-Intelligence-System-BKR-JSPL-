import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend/inventory.db')
print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()
tables = ['damage_claims', 'fc_return_items', 'fc_returns', 'fc_dispatch_items', 'fc_dispatches']
for table in tables:
    try:
        c.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"Dropped {table}")
    except Exception as e:
        print(f"Error dropping {table}: {e}")
conn.commit()
conn.close()
print("Tables dropped.")
