import psycopg2
import psycopg2.extras
import os

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id, company_id, invoice_number FROM sales WHERE id = 49")
print(cur.fetchone())

cur.execute("SELECT id, name, code FROM companies")
print(cur.fetchall())
