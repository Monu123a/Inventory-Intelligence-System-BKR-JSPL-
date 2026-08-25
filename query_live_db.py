import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT id, name, code, warehouse_type, company_id FROM warehouses WHERE company_id IN (1, 2);")
warehouses = cur.fetchall()

print("LIVE WAREHOUSES:")
for w in warehouses:
    print(dict(w))

cur.execute("SELECT warehouse_id, SUM(current_qty) as total_qty FROM inventory GROUP BY warehouse_id;")
inv = cur.fetchall()
print("\nLIVE INVENTORY TOTALS:")
for i in inv:
    print(dict(i))

conn.close()
