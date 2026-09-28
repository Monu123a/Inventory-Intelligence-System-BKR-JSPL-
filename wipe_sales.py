import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

queries = [
    # Delete sale items for sales > 20
    "DELETE FROM sale_items WHERE sale_id > 20;",
    
    # Delete sales > 20
    "DELETE FROM sales WHERE id > 20;"
]

for sql in queries:
    try:
        cur.execute(sql)
        print(f"Executed: {sql[:50]}... | Deleted: {cur.rowcount}")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        break
else:
    conn.commit()
    print("SUCCESS: Sales deleted!")

cur.close()
conn.close()
