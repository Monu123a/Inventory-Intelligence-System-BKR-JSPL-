import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

cur.execute("SELECT id, created_at, company_id FROM sales ORDER BY id DESC LIMIT 10;")
print("Sales:", cur.fetchall())

