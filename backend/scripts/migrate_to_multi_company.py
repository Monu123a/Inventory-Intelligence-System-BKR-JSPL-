import sqlite3
import os
import sys

def migrate():
    db_path = 'inventory.db'
    new_db_path = 'inventory_new.db'
    
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    # Backup
    import shutil
    shutil.copy2(db_path, 'inventory.db.bak')
    print("Created backup at inventory.db.bak")
    
    if os.path.exists(new_db_path):
        os.remove(new_db_path)

    # Use SQLAlchemy to create new tables in the NEW database
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sqlalchemy import create_engine
    from app.models.db import Base
    import app.models.schema # this registers the new schema
    
    new_engine = create_engine(f"sqlite:///{new_db_path}")
    Base.metadata.create_all(bind=new_engine)

    # Connect to the new database and ATTACH the old one
    conn = sqlite3.connect(new_db_path)
    cur = conn.cursor()
    
    cur.execute(f"ATTACH DATABASE '{db_path}' AS old_db")

    try:
        # Insert Companies
        cur.execute("INSERT INTO companies (name, code) VALUES ('JSPL', 'JSPL')")
        cur.execute("INSERT INTO companies (name, code) VALUES ('BKR', 'BKR')")
        conn.commit()

        # Copy users and give them access
        cur.execute("INSERT INTO users (id, username, password_hash, role, created_at) SELECT id, username, password_hash, role, created_at FROM old_db.users")
        
        cur.execute("SELECT id FROM users")
        users = cur.fetchall()
        for (user_id,) in users:
            for company_id in (1, 2):
                cur.execute("INSERT INTO company_users (user_id, company_id) VALUES (?, ?)", (user_id, company_id))
        conn.commit()

        # Products
        cur.execute("PRAGMA old_db.table_info(products)")
        if cur.fetchall():
            print("Migrating products...")
            cur.execute("SELECT sku, name, category, brand, item_rate, min_stock_level, status, hsn, barcode, unit FROM old_db.products")
            old_prods = cur.fetchall()
            for p in old_prods:
                cur.execute("""
                    INSERT INTO products (company_id, sku, name, category, brand, item_rate, min_stock_level, status, hsn, barcode, unit)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, p)
            conn.commit()

        # Build a sku -> product_id map
        cur.execute("SELECT sku, id FROM products WHERE company_id = 1")
        sku_to_id = {row[0]: row[1] for row in cur.fetchall()}

        # Warehouses
        cur.execute("PRAGMA old_db.table_info(warehouses)")
        if cur.fetchall():
            print("Migrating warehouses...")
            cur.execute("SELECT id, name, code, status, address, contact_person, phone_number, email FROM old_db.warehouses")
            for w in cur.fetchall():
                cur.execute("""
                    INSERT INTO warehouses (id, company_id, name, code, status, address, contact_person, phone_number, email)
                    VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)
                """, w)
            conn.commit()

        # Inventory
        cur.execute("PRAGMA old_db.table_info(inventory)")
        if cur.fetchall():
            print("Migrating inventory...")
            cur.execute("SELECT id, product_sku, warehouse_id, current_qty, reserved_qty, available_qty, last_updated FROM old_db.inventory")
            for inv in cur.fetchall():
                prod_id = sku_to_id.get(inv[1])
                if prod_id:
                    cur.execute("""
                        INSERT INTO inventory (id, company_id, product_id, warehouse_id, current_qty, reserved_qty, available_qty, last_updated)
                        VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                    """, (inv[0], prod_id, inv[2], inv[3], inv[4], inv[5], inv[6]))
            conn.commit()

        # Inventory Movements
        cur.execute("PRAGMA old_db.table_info(inventory_movements)")
        if cur.fetchall():
            print("Migrating inventory_movements...")
            cur.execute("SELECT id, timestamp, product_sku, warehouse_id, qty_before, qty_changed, qty_after, source, reference_id, user_id, metadata_payload FROM old_db.inventory_movements")
            for mv in cur.fetchall():
                prod_id = sku_to_id.get(mv[2])
                if prod_id:
                    cur.execute("""
                        INSERT INTO inventory_movements (id, company_id, timestamp, product_id, warehouse_id, qty_before, qty_changed, qty_after, source, reference_id, user_id, metadata_payload)
                        VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (mv[0], mv[1], prod_id, mv[3], mv[4], mv[5], mv[6], mv[7], mv[8], mv[9], mv[10]))
            conn.commit()

        # Simple tables (just add company_id = 1)
        simple_tables = [
            ('amazon_sync_logs', "id, order_id, sync_start_time, sync_end_time, status, api_response_status, orders_processed, movements_created, skipped_duplicates, failed_items, unknown_skus, next_token, errors"),
            ('reports_history', "id, report_type, generated_at, file_path, download_link"),
            ('alerts', "id, timestamp, alert_type, message, is_resolved"),
            ('job_execution_logs', "id, job_name, start_time, end_time, duration_seconds, status, error_message")
        ]

        for table, cols in simple_tables:
            cur.execute(f"PRAGMA old_db.table_info({table})")
            if cur.fetchall():
                print(f"Migrating {table}...")
                cur.execute(f"SELECT {cols} FROM old_db.{table}")
                rows = cur.fetchall()
                if rows:
                    placeholders = ", ".join(["?"] * (len(cols.split(",")) + 1))
                    insert_query = f"INSERT INTO {table} ({cols.replace('id, ', 'id, company_id, ', 1)}) VALUES ({placeholders})"
                    
                    for row in rows:
                        new_row = list(row)
                        new_row.insert(1, 1) # Insert company_id = 1 after id
                        cur.execute(insert_query, new_row)
                conn.commit()
                
        # Snapshots
        cur.execute("PRAGMA old_db.table_info(inventory_snapshots)")
        if cur.fetchall():
            print("Migrating inventory_snapshots...")
            cur.execute("SELECT id, date, warehouse_id, product_sku, quantity FROM old_db.inventory_snapshots")
            for sn in cur.fetchall():
                prod_id = sku_to_id.get(sn[3])
                if prod_id:
                    cur.execute("""
                        INSERT INTO inventory_snapshots (id, company_id, date, warehouse_id, product_id, quantity)
                        VALUES (?, 1, ?, ?, ?, ?)
                    """, (sn[0], sn[1], sn[2], prod_id, sn[4]))
            conn.commit()
            
        # Swap the databases
        conn.close()
        os.remove(db_path)
        os.rename(new_db_path, db_path)
        print("Migration complete! Database replaced with new schema.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        conn.close()

if __name__ == "__main__":
    migrate()
