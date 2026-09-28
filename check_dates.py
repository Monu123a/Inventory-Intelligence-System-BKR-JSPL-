import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

cur.execute("SELECT id, timestamp FROM inventory_movements ORDER BY id DESC LIMIT 5;")
print("Recent movements:", cur.fetchall())

cur.execute("SELECT id, created_at FROM fc_dispatches ORDER BY id DESC LIMIT 5;")
print("Recent dispatches:", cur.fetchall())

cur.execute("SELECT id, created_at FROM stock_transfers ORDER BY id DESC LIMIT 5;")
print("Recent transfers:", cur.fetchall())

cur.close()
conn.close()
