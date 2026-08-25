import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT SUM(current_qty) as current, SUM(reserved_qty) as reserved, SUM(available_qty) as available FROM inventory WHERE warehouse_id = 39;")
print(cur.fetchone())
conn.close()
