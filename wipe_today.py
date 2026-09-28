import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

# We want to wipe all transactions created on Aug 25 (today) or later
query = "DELETE FROM {table} WHERE {date_col} >= '2026-08-21';"

tables = [
    ('inventory_movements', 'timestamp'),
    ('fc_dispatch_items', 'id IN (SELECT id FROM fc_dispatches WHERE created_at >= \'2026-08-21\') --'),
    ('fc_dispatches', 'created_at'),
    ('delivery_challan_items', 'id IN (SELECT id FROM delivery_challans WHERE challan_date >= \'2026-08-21\') --'),
    ('delivery_challans', 'challan_date'),
    ('stock_transfer_items', 'id IN (SELECT id FROM stock_transfers WHERE created_at >= \'2026-08-21\') --'),
    ('stock_transfers', 'created_at'),
    ('sale_items', 'id IN (SELECT id FROM sales WHERE created_at >= \'2026-08-21\') --'),
    ('sales', 'created_at')
]

for tbl, date_col in tables:
    if '--' in date_col:
        sql = f"DELETE FROM {tbl} WHERE {date_col}"
    else:
        sql = f"DELETE FROM {tbl} WHERE {date_col} >= '2026-08-21';"
    try:
        cur.execute(sql)
        print(f"Deleted {cur.rowcount} rows from {tbl}")
    except Exception as e:
        print(f"Error on {tbl}: {e}")
        conn.rollback()

conn.commit()
cur.close()
conn.close()
