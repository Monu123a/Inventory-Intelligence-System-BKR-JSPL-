import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

queries = {
    'sales': 'SELECT id, bill_number FROM sales ORDER BY id DESC LIMIT 10;',
    'fc_dispatches': 'SELECT id, dispatch_number FROM fc_dispatches ORDER BY id DESC LIMIT 10;',
    'delivery_challans': 'SELECT id, challan_number FROM delivery_challans ORDER BY id DESC LIMIT 10;',
    'stock_transfers': 'SELECT id, transfer_number FROM stock_transfers ORDER BY id DESC LIMIT 10;',
    'inventory_movements': 'SELECT id, timestamp FROM inventory_movements ORDER BY id DESC LIMIT 10;'
}

for name, q in queries.items():
    print(f"--- {name} ---")
    cur.execute(q)
    for r in cur.fetchall():
        print(r)

cur.close()
conn.close()
