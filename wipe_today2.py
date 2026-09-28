import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
conn = psycopg2.connect(RENDER_POSTGRES_URL)
cur = conn.cursor()

queries = [
    # 1. Delete timeline and items referencing dispatches >= Aug 21
    "DELETE FROM dispatch_timeline WHERE dispatch_id IN (SELECT id FROM fc_dispatches WHERE created_at >= '2026-08-21');",
    "DELETE FROM fc_dispatch_items WHERE dispatch_id IN (SELECT id FROM fc_dispatches WHERE created_at >= '2026-08-21');",
    
    # 2. Delete dispatches themselves (but first disconnect challans)
    "UPDATE fc_dispatches SET delivery_challan_id = NULL WHERE created_at >= '2026-08-21';",
    "DELETE FROM fc_dispatches WHERE created_at >= '2026-08-21';",
    
    # 3. Delete Challan items
    "DELETE FROM delivery_challan_items WHERE challan_id IN (SELECT id FROM delivery_challans WHERE challan_date >= '2026-08-21');",
    
    # 4. Delete Challans
    "DELETE FROM delivery_challans WHERE challan_date >= '2026-08-21';",
    
    # 5. Delete Transfer items
    "DELETE FROM stock_transfer_items WHERE transfer_id IN (SELECT id FROM stock_transfers WHERE created_at >= '2026-08-21');",
    
    # 6. Delete Transfers
    "DELETE FROM stock_transfers WHERE created_at >= '2026-08-21';",
    
    # 7. Delete Sale items
    "DELETE FROM sale_items WHERE sale_id IN (SELECT id FROM sales WHERE created_at >= '2026-08-21');",
    
    # 8. Delete Sales
    "DELETE FROM sales WHERE created_at >= '2026-08-21';",
    
    # 9. Delete movements
    "DELETE FROM inventory_movements WHERE timestamp >= '2026-08-21';"
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
    print("SUCCESS: All new records wiped!")

cur.close()
conn.close()
