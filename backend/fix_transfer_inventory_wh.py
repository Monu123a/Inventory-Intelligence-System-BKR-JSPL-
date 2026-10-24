import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Update stock_transfers destination_warehouse_id for TR-ST-4B0F12 (invoice GST-547)
            cur.execute("""
                UPDATE stock_transfers
                SET destination_warehouse_id = 14
                WHERE id = 73 AND invoice_id = 212;
            """)
            print(f"Updated stock_transfers destination: {cur.rowcount} record(s)")

            # 2. Fix Inventory for BLR4 (id 18) - deduct wrongly added quantities
            cur.execute("""
                UPDATE inventory SET current_qty = current_qty - 7, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 18 AND product_id = 704; -- HM0675
            """)
            print(f"Deducted HM0675 from BLR4: {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory SET current_qty = current_qty - 2, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 18 AND product_id = 817; -- LG0738
            """)
            print(f"Deducted LG0738 from BLR4: {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory SET current_qty = current_qty - 1, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 18 AND product_id = 1016; -- LG1042
            """)
            print(f"Deducted LG1042 from BLR4: {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory SET current_qty = current_qty - 1, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 18 AND product_id = 1115; -- LG1149
            """)
            print(f"Deducted LG1149 from BLR4: {cur.rowcount} record(s)")

            # 3. Fix Inventory for Central VSHB (id 14) - add quantities
            cur.execute("""
                UPDATE inventory SET current_qty = current_qty + 7, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 14 AND product_id = 704; -- HM0675
            """)
            print(f"Added HM0675 to VSHB: {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory SET current_qty = current_qty + 2, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 14 AND product_id = 817; -- LG0738
            """)
            print(f"Added LG0738 to VSHB: {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory SET current_qty = current_qty + 1, last_updated = NOW()
                WHERE company_id = 3 AND warehouse_id = 14 AND product_id = 1016; -- LG1042
            """)
            print(f"Added LG1042 to VSHB: {cur.rowcount} record(s)")

            # For LG1149, check if row exists in VSHB; if not, insert it
            cur.execute("""
                SELECT id, current_qty FROM inventory 
                WHERE company_id = 3 AND warehouse_id = 14 AND product_id = 1115;
            """)
            existing_lg1149 = cur.fetchone()
            if existing_lg1149:
                cur.execute("""
                    UPDATE inventory SET current_qty = current_qty + 1, last_updated = NOW()
                    WHERE id = %s;
                """, (existing_lg1149[0],))
                print(f"Updated LG1149 in VSHB: {cur.rowcount} record(s)")
            else:
                cur.execute("""
                    INSERT INTO inventory (company_id, warehouse_id, product_id, current_qty, reserved_qty, last_updated)
                    VALUES (3, 14, 1115, 1, 0, NOW());
                """)
                print(f"Inserted LG1149 into VSHB: {cur.rowcount} record(s)")

            # 4. Update inventory_movements records (1824, 1826, 1828, 1830) so history shows VSHB
            cur.execute("""
                UPDATE inventory_movements
                SET warehouse_id = 14, qty_before = 218, qty_changed = 7, qty_after = 225
                WHERE id = 1824;
            """)
            print(f"Updated movement 1824 (HM0675): {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory_movements
                SET warehouse_id = 14, qty_before = 13, qty_changed = 2, qty_after = 15
                WHERE id = 1826;
            """)
            print(f"Updated movement 1826 (LG0738): {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory_movements
                SET warehouse_id = 14, qty_before = 7, qty_changed = 1, qty_after = 8
                WHERE id = 1828;
            """)
            print(f"Updated movement 1828 (LG1042): {cur.rowcount} record(s)")

            cur.execute("""
                UPDATE inventory_movements
                SET warehouse_id = 14, qty_before = 0, qty_changed = 1, qty_after = 1
                WHERE id = 1830;
            """)
            print(f"Updated movement 1830 (LG1149): {cur.rowcount} record(s)")

            conn.commit()
            print("Successfully committed all inventory and movement corrections!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
