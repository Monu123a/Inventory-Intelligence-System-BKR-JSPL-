import os
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

def run_transfer(dry_run=True):
    load_dotenv('backend/.env')
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not found in backend/.env")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # 1. Fetch Source Warehouse
        cur.execute("SELECT id, code, name, company_id FROM warehouses WHERE id = 6 OR code = 'WH-6';")
        src_wh = cur.fetchone()
        if not src_wh:
            print("ERROR: Source warehouse WH-6 (ID 6) not found!")
            return

        # 2. Fetch Target Warehouse
        cur.execute("SELECT id, code, name, company_id FROM warehouses WHERE id = 14 OR code = 'VSHB';")
        tgt_wh = cur.fetchone()
        if not tgt_wh:
            print("ERROR: Target warehouse VSHB (ID 14) not found!")
            return

        print(f"Source Warehouse: ID={src_wh[0]}, Code={src_wh[1]}, Name={src_wh[2]}")
        print(f"Target Warehouse: ID={tgt_wh[0]}, Code={tgt_wh[1]}, Name={tgt_wh[2]}")
        print("="*80)

        # 3. Fetch inventory items to transfer
        cur.execute("""
            SELECT 
                p.id as product_id,
                p.sku,
                p.name as product_name,
                src.current_qty as src_qty,
                src.available_qty as src_avail,
                src.reserved_qty as src_reserved,
                COALESCE(tgt.current_qty, 0) as tgt_qty,
                COALESCE(tgt.available_qty, 0) as tgt_avail,
                COALESCE(tgt.reserved_qty, 0) as tgt_reserved,
                tgt.id as tgt_inv_id
            FROM inventory src
            JOIN products p ON src.product_id = p.id
            LEFT JOIN inventory tgt ON tgt.product_id = p.id AND tgt.warehouse_id = %s
            WHERE src.warehouse_id = %s
            ORDER BY p.sku;
        """, (tgt_wh[0], src_wh[0]))
        items = cur.fetchall()

        print(f"{'SKU':<16} | {'Product Name':<38} | {'WH-6 Qty':<8} | {'VSHB Current':<12} | {'VSHB After':<10}")
        print("-" * 88)
        
        total_src_qty = 0
        total_tgt_current = 0
        total_tgt_new = 0

        updates = []
        inserts = []

        for row in items:
            prod_id, sku, name, s_qty, s_avail, s_res, t_qty, t_avail, t_res, t_inv_id = row
            new_qty = t_qty + s_qty
            new_avail = t_avail + s_avail
            new_res = t_res + s_res

            total_src_qty += s_qty
            total_tgt_current += t_qty
            total_tgt_new += new_qty

            name_trunc = name[:36] if name else ""
            print(f"{sku:<16} | {name_trunc:<38} | {s_qty:<8} | {t_qty:<12} | {new_qty:<10}")

            if t_inv_id:
                updates.append((new_qty, new_avail, new_res, t_inv_id))
            else:
                inserts.append((src_wh[3], prod_id, tgt_wh[0], s_qty, s_res, s_avail))

        print("-" * 88)
        print(f"TOTALS: WH-6 Units = {total_src_qty} | VSHB Current = {total_tgt_current} | VSHB Combined = {total_tgt_new}")
        print("="*80)

        # 4. Check historical inventory movements
        cur.execute("SELECT count(*) FROM inventory_movements WHERE warehouse_id = %s;", (src_wh[0],))
        movements_count = cur.fetchone()[0]
        print(f"Historical inventory movements referencing WH-6: {movements_count}")

        if dry_run:
            print("\n[DRY RUN MODE] No changes have been applied to the database.")
            print("To execute this transfer and removal, run with --execute")
            return

        print("\n[EXECUTE MODE] Applying changes...")

        # A. Update existing target inventory rows
        if updates:
            execute_values(
                cur,
                """
                UPDATE inventory AS i
                SET 
                    current_qty = v.current_qty,
                    available_qty = v.available_qty,
                    reserved_qty = v.reserved_qty,
                    last_updated = NOW()
                FROM (VALUES %s) AS v(current_qty, available_qty, reserved_qty, id)
                WHERE i.id = v.id;
                """,
                updates
            )
            print(f"Updated {len(updates)} inventory records in VSHB (Central fc).")

        # B. Insert any missing target inventory rows
        if inserts:
            execute_values(
                cur,
                """
                INSERT INTO inventory (company_id, product_id, warehouse_id, current_qty, reserved_qty, available_qty, version_id, last_updated)
                VALUES %s;
                """,
                [(c_id, p_id, w_id, c_qty, r_qty, a_qty, 1) for c_id, p_id, w_id, c_qty, r_qty, a_qty in inserts]
            )
            print(f"Inserted {len(inserts)} new inventory records into VSHB (Central fc).")

        # C. Re-point historical movements from warehouse 6 to warehouse 14
        if movements_count > 0:
            cur.execute("""
                UPDATE inventory_movements
                SET warehouse_id = %s
                WHERE warehouse_id = %s;
            """, (tgt_wh[0], src_wh[0]))
            print(f"Re-linked {cur.rowcount} inventory movements from WH-6 to VSHB.")

        # D. Delete inventory rows of warehouse 6
        cur.execute("DELETE FROM inventory WHERE warehouse_id = %s;", (src_wh[0],))
        print(f"Deleted {cur.rowcount} inventory rows from WH-6.")

        # E. Delete warehouse WH-6
        cur.execute("DELETE FROM warehouses WHERE id = %s;", (src_wh[0],))
        print(f"Successfully deleted warehouse WH-6 (ID {src_wh[0]}).")

        # F. Commit
        conn.commit()
        print("\nAll database updates successfully committed!")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: Transaction failed and was rolled back: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Transfer inventory from WH-6 to VSHB and remove WH-6.")
    parser.add_argument('--execute', action='store_true', help="Actually execute the updates against the database.")
    args = parser.parse_args()

    run_transfer(dry_run=not args.execute)
