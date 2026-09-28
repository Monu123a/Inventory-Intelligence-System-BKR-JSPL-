import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

cur.execute("SELECT id FROM inventory_movements WHERE id <= 22;")
print("Movements <= 22:", cur.fetchall())

cur.execute("SELECT id FROM fc_dispatches WHERE id <= 21;")
print("Dispatches <= 21:", cur.fetchall())

cur.execute("SELECT id FROM stock_transfers WHERE id <= 11;")
print("Transfers <= 11:", cur.fetchall())

cur.close()
conn.close()
