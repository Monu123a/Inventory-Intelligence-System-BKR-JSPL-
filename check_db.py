import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM inventory_movements;")
print("Inventory movements:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM fc_dispatches;")
print("FC Dispatches:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM stock_transfers;")
print("Stock Transfers:", cur.fetchone()[0])

cur.close()
conn.close()
