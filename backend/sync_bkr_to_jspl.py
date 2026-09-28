import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Get all products in JSPL
    cursor.execute("SELECT id FROM products WHERE company_id = 3")
    jspl_product_ids = [row[0] for row in cursor.fetchall()]

    # Get all active JSPL warehouses
    cursor.execute("SELECT id FROM warehouses WHERE company_id = 3 AND status = 'ACTIVE'")
    jspl_warehouse_ids = [row[0] for row in cursor.fetchall()]

    # Get existing inventory pairs
    cursor.execute("SELECT product_id, warehouse_id FROM inventory WHERE company_id = 3")
    existing_pairs = set((row[0], row[1]) for row in cursor.fetchall())

    inventory_inserts = []
    for prod_id in jspl_product_ids:
        for wh_id in jspl_warehouse_ids:
            if (prod_id, wh_id) not in existing_pairs:
                # version_id usually defaults to 1, but we should supply it if there's no default
                inventory_inserts.append((3, wh_id, prod_id, 0, 0, 0, 1))
                
    if inventory_inserts:
        inv_query = """
            INSERT INTO inventory (company_id, warehouse_id, product_id, current_qty, available_qty, reserved_qty, version_id)
            VALUES %s
        """
        execute_values(cursor, inv_query, inventory_inserts)
        print(f"Initialized zero inventory for {len(inventory_inserts)} missing warehouse-product combinations in JSPL.")
    else:
        print("All JSPL warehouse-product combinations already have inventory records.")
        
    conn.commit()
    print("Sync complete.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
