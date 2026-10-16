import os
import sys
import json
import argparse
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Merge Auto Godown (WH 2) inventory into BKR Central (WH 39).")
    parser.add_argument("--commit", action="store_true", help="Execute database changes. Defaults to dry-run.")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Fetch all inventory from Auto Godown (WH 2)
        cur.execute("""
            SELECT 
                i.id AS inv2_id,
                i.product_id,
                p.sku,
                p.name,
                i.company_id,
                i.current_qty AS wh2_current,
                i.available_qty AS wh2_available,
                i.reserved_qty AS wh2_reserved,
                c.id AS inv39_id,
                COALESCE(c.current_qty, 0) AS wh39_current,
                COALESCE(c.available_qty, 0) AS wh39_available,
                COALESCE(c.reserved_qty, 0) AS wh39_reserved
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            LEFT JOIN inventory c ON c.product_id = i.product_id AND c.warehouse_id = 39
            WHERE i.warehouse_id = 2
            ORDER BY p.sku ASC
        """)
        rows = cur.fetchall()

        if not rows:
            print("No inventory records found in Auto Godown (warehouse_id = 2).")
            return

        print("\n" + "=" * 105)
        print("INVENTORY MERGE DRY RUN: Auto Godown (WH 2) -> BKR Central (WH 39)")
        print("=" * 105)
        print(f"{'SKU':<14} | {'Product Name':<35} | {'WH 2 Qty':<10} | {'WH 39 Current':<15} | {'Merged WH 39':<14} | {'Status'}")
        print("-" * 105)

        total_wh2_qty = 0
        total_wh39_current = 0
        total_merged_qty = 0
        to_update_39 = []
        to_insert_39 = []
        wh2_zero_ids = []
        movements = []

        for r in rows:
            inv2_id, prod_id, sku, name, comp_id, wh2_curr, wh2_avail, wh2_res, inv39_id, wh39_curr, wh39_avail, wh39_res = r
            
            merged_curr = wh39_curr + wh2_curr
            merged_avail = wh39_avail + wh2_avail

            total_wh2_qty += wh2_curr
            total_wh39_current += wh39_curr
            total_merged_qty += merged_curr

            status = "UPDATE WH 39" if inv39_id else "NEW INSERT WH 39"
            print(f"{sku:<14} | {name[:35]:<35} | {wh2_curr:<10} | {wh39_curr:<15} | {merged_curr:<14} | {status}")

            if wh2_curr > 0 or wh2_avail > 0:
                wh2_zero_ids.append(inv2_id)
                if inv39_id:
                    to_update_39.append((merged_curr, merged_avail, inv39_id))
                else:
                    to_insert_39.append((comp_id, prod_id, 39, wh2_curr, wh2_avail, 0, 1))

                # Movement OUT of WH 2
                movements.append((
                    comp_id, prod_id, 2, wh2_curr, -wh2_curr, 0,
                    'INTERNAL_TRANSFER', 'MERGE_AUTO_TO_CENTRAL',
                    json.dumps({"note": f"Merged {wh2_curr} units to BKR Central (WH 39)", "sku": sku})
                ))
                # Movement IN to WH 39
                movements.append((
                    comp_id, prod_id, 39, wh39_curr, wh2_curr, merged_curr,
                    'INTERNAL_TRANSFER', 'MERGE_AUTO_TO_CENTRAL',
                    json.dumps({"note": f"Merged {wh2_curr} units from Auto Godown (WH 2)", "sku": sku})
                ))

        print("-" * 105)
        print(f"Total SKUs in Auto Godown: {len(rows)}")
        print(f"Total Quantity in Auto Godown (WH 2): {total_wh2_qty}")
        print(f"Current Quantity in BKR Central (WH 39): {total_wh39_current}")
        print(f"Total Quantity in BKR Central after Merge: {total_merged_qty}")
        print(f"Rows to Update in WH 39: {len(to_update_39)}")
        print(f"Rows to Insert in WH 39: {len(to_insert_39)}")
        print("=" * 105 + "\n")

        if not args.commit:
            print(">> DRY RUN COMPLETE: No database modifications were committed.")
            print(">> To execute this merge, run: python backend/merge_auto_godown_to_central.py --commit\n")
            return

        print("Executing bulk database updates using psycopg2 execute_values...")

        # 1. Update existing WH 39 inventory rows
        if to_update_39:
            execute_values(
                cur,
                """
                UPDATE inventory AS i
                SET current_qty = data.merged_curr,
                    available_qty = data.merged_avail,
                    last_updated = NOW()
                FROM (VALUES %s) AS data (merged_curr, merged_avail, id)
                WHERE i.id = data.id
                """,
                to_update_39
            )
            print(f"  ✓ Updated {len(to_update_39)} existing rows in BKR Central (WH 39).")

        # 2. Insert missing WH 39 inventory rows
        if to_insert_39:
            execute_values(
                cur,
                """
                INSERT INTO inventory (company_id, product_id, warehouse_id, current_qty, available_qty, reserved_qty, version_id, last_updated)
                VALUES %s
                """,
                to_insert_39,
                template="(%s, %s, %s, %s, %s, %s, %s, NOW())"
            )
            print(f"  ✓ Inserted {len(to_insert_39)} new rows in BKR Central (WH 39).")

        # 3. Reset Auto Godown (WH 2) inventory quantities to 0
        if wh2_zero_ids:
            cur.execute("""
                UPDATE inventory
                SET current_qty = 0,
                    available_qty = 0,
                    last_updated = NOW()
                WHERE id = ANY(%s)
            """, (wh2_zero_ids,))
            print(f"  ✓ Reset {len(wh2_zero_ids)} Auto Godown (WH 2) inventory rows to 0 stock.")

        # 4. Record audit movements in inventory_movements
        if movements:
            execute_values(
                cur,
                """
                INSERT INTO inventory_movements (
                    company_id, timestamp, product_id, warehouse_id, qty_before, qty_changed,
                    qty_after, source, reference_id, metadata_payload
                )
                VALUES %s
                """,
                movements,
                template="(%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            print(f"  ✓ Inserted {len(movements)} inventory movement audit records.")

        conn.commit()
        print("\n>> SUCCESS: Successfully merged Auto Godown into BKR Central and committed transaction!\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: Merge failed, rolled back all changes: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
