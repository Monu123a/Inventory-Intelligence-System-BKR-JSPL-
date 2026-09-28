import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

def check(q):
    cur.execute(q)
    return cur.fetchall()

print("Dispatches:", check("SELECT id, dispatch_number FROM fc_dispatches ORDER BY id DESC LIMIT 1"))
print("Challans:", check("SELECT id, challan_number FROM delivery_challans ORDER BY id DESC LIMIT 1"))
print("Transfers:", check("SELECT id, transfer_number FROM stock_transfers ORDER BY id DESC LIMIT 1"))
print("Sales:", check("SELECT id, bill_number FROM sales ORDER BY id DESC LIMIT 1"))
print("Movements:", check("SELECT id FROM inventory_movements ORDER BY id DESC LIMIT 1"))

cur.close()
conn.close()
