"""
Migration script to:
1. Add order_date, invoice_number, invoice_date columns to amazon_live_allocations.
2. Backfill existing JSPL MFN allocations to warehouse_id = 38 (JSPL IN) and populate order_date/invoice_date/invoice_number.
3. Import historical Amazon MTR orders from backend/uploads/raw-amazon-data.xlsx into amazon_live_allocations
   with exact Invoice Numbers (e.g. IN-274, VSHB-420), Invoice Dates, and Order Dates.
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

def run_migration():
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Step 1: Add columns if not exist
        print("\n--- STEP 1: ADDING SCHEMA COLUMNS ---")
        cur.execute("""
            ALTER TABLE amazon_live_allocations 
            ADD COLUMN IF NOT EXISTS order_date TIMESTAMP WITHOUT TIME ZONE;

            ALTER TABLE amazon_live_allocations 
            ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(255);

            ALTER TABLE amazon_live_allocations 
            ADD COLUMN IF NOT EXISTS invoice_date TIMESTAMP WITHOUT TIME ZONE;

            CREATE INDEX IF NOT EXISTS idx_alloc_order_date ON amazon_live_allocations(order_date);
            CREATE INDEX IF NOT EXISTS idx_alloc_invoice_number ON amazon_live_allocations(invoice_number);
        """)
        print("Columns and indexes ensured.")

        # Step 2: Fetch active JSPL warehouses for mapping
        cur.execute("SELECT id, UPPER(code) FROM warehouses WHERE company_id = 3")
        wh_map = {r[1]: r[0] for r in cur.fetchall()}
        print(f"JSPL Warehouses found: {wh_map}")
        wh_in_id = wh_map.get("IN", 38)

        # Step 3: Update existing JSPL MFN allocations in DB
        print("\n--- STEP 2: UPDATING EXISTING JSPL MFN ALLOCATIONS ---")
        cur.execute("""
            UPDATE amazon_live_allocations
            SET warehouse_id = %s
            WHERE company_id = 3 
              AND amazon_network_at_allocation = 'MFN' 
              AND (warehouse_id IS NULL OR warehouse_id = 14);
        """, (wh_in_id,))
        updated_mfn = cur.rowcount
        print(f"Updated {updated_mfn} JSPL MFN allocations to warehouse_id={wh_in_id} (JSPL IN).")

        # Step 4: Backfill order_date, invoice_date, invoice_number for existing allocations where missing
        cur.execute("""
            UPDATE amazon_live_allocations a
            SET 
                order_date = COALESCE(a.order_date, a.updated_at, a.created_at),
                invoice_date = COALESCE(a.invoice_date, a.updated_at, a.created_at),
                invoice_number = COALESCE(
                    a.invoice_number,
                    CASE 
                        WHEN a.amazon_network_at_allocation = 'MFN' OR a.warehouse_id = 38 THEN 
                            'IN-' || RIGHT(REGEXP_REPLACE(a.order_id, '[^0-9]', '', 'g'), 6)
                        ELSE 
                            COALESCE(w.code, 'AMZ') || '-' || RIGHT(REGEXP_REPLACE(a.order_id, '[^0-9]', '', 'g'), 6)
                    END
                )
            FROM warehouses w
            WHERE a.warehouse_id = w.id
              AND (a.order_date IS NULL OR a.invoice_number IS NULL OR a.invoice_date IS NULL);
        """)
        backfilled_allocs = cur.rowcount
        print(f"Backfilled order_date/invoice_date/invoice_number for {backfilled_allocs} existing allocations.")

        # Step 5: Import raw-amazon-data.xlsx
        excel_path = os.path.join(os.path.dirname(__file__), "uploads", "raw-amazon-data.xlsx")
        if os.path.exists(excel_path):
            print(f"\n--- STEP 3: IMPORTING {excel_path} ---")
            df = pd.read_excel(excel_path)
            print(f"Loaded {len(df)} rows from excel.")

            records_to_upsert = []
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            for idx, row in df.iterrows():
                order_id = str(row.get("Order Id", "")).strip()
                if not order_id or order_id == "nan":
                    continue

                sku = str(row.get("Sku", "")).strip()
                if not sku or sku == "nan":
                    continue

                raw_line_id = str(row.get("Shipment Item Id", "")).strip()
                trans_type = str(row.get("Transaction Type", "Shipment")).strip().lower()
                # Disambiguate line_item_id per row to ensure 100% uniqueness within batch
                line_item_id = f"{raw_line_id}_{trans_type}_{idx}" if (raw_line_id and raw_line_id != "nan") else f"item-{idx}_{trans_type}"

                raw_inv_num = row.get("Invoice Number")
                invoice_num = str(raw_inv_num).strip() if pd.notna(raw_inv_num) and str(raw_inv_num).strip() != "nan" else None

                raw_inv_dt = row.get("Invoice Date")
                inv_dt = pd.to_datetime(raw_inv_dt).to_pydatetime() if pd.notna(raw_inv_dt) else None

                raw_ord_dt = row.get("Order Date")
                ord_dt = pd.to_datetime(raw_ord_dt).to_pydatetime() if pd.notna(raw_ord_dt) else (inv_dt or now)
                if not inv_dt:
                    inv_dt = ord_dt

                qty = int(row.get("Quantity", 1)) if pd.notna(row.get("Quantity")) else 1
                channel_str = str(row.get("Fulfillment Channel", "")).strip().upper()

                # Determine network and warehouse
                if invoice_num and invoice_num.upper().startswith("IN-"):
                    network = "MFN"
                    target_wh_id = wh_in_id
                elif channel_str == "MFN":
                    network = "MFN"
                    target_wh_id = wh_in_id
                else:
                    network = "AFN"
                    pfx = invoice_num.split("-")[0].strip().upper() if invoice_num and "-" in invoice_num else ""
                    target_wh_id = wh_map.get(pfx, wh_map.get("VSHB", 14))

                if not invoice_num:
                    if network == "MFN":
                        invoice_num = f"IN-{order_id.replace('-', '')[-6:]}"
                    else:
                        target_wh_code = [k for k, v in wh_map.items() if v == target_wh_id]
                        wh_code = target_wh_code[0] if target_wh_code else "VSHB"
                        invoice_num = f"{wh_code}-{order_id.replace('-', '')[-6:]}"

                if trans_type in ("cancel", "cancelled"):
                    status = "CANCELLED"
                    closed = True
                    allocated_qty = 0
                elif trans_type in ("refund", "returned"):
                    status = "RETURNED"
                    closed = True
                    allocated_qty = 0
                else:
                    status = "SHIPPED"
                    closed = False
                    allocated_qty = qty

                created_at = ord_dt
                updated_at = inv_dt

                records_to_upsert.append((
                    3,                     # company_id = 3 (JSPL)
                    order_id,              # order_id
                    line_item_id,          # amazon_line_item_id
                    sku,                   # sku (strict variant isolation)
                    target_wh_id,          # warehouse_id
                    network,               # amazon_network_at_allocation
                    allocated_qty,         # allocated_qty
                    0,                     # reconciled_qty
                    status,                # status
                    closed,                # closed
                    ord_dt,                # order_date
                    invoice_num,           # invoice_number
                    inv_dt,                # invoice_date
                    created_at,            # created_at
                    updated_at             # updated_at
                ))

            print(f"Prepared {len(records_to_upsert)} Amazon records for upsert.")
            upsert_query = """
                INSERT INTO amazon_live_allocations (
                    company_id, order_id, amazon_line_item_id, sku,
                    warehouse_id, amazon_network_at_allocation, allocated_qty,
                    reconciled_qty, status, closed, order_date, invoice_number,
                    invoice_date, created_at, updated_at
                ) VALUES %s
                ON CONFLICT (order_id, sku, amazon_line_item_id)
                DO UPDATE SET
                    order_date = EXCLUDED.order_date,
                    invoice_number = EXCLUDED.invoice_number,
                    invoice_date = EXCLUDED.invoice_date,
                    warehouse_id = EXCLUDED.warehouse_id,
                    amazon_network_at_allocation = EXCLUDED.amazon_network_at_allocation,
                    updated_at = EXCLUDED.updated_at;
            """
            execute_values(cur, upsert_query, records_to_upsert, page_size=250)
            print(f"Successfully upserted {len(records_to_upsert)} records into amazon_live_allocations.")

        conn.commit()
        print("\nAll changes committed successfully!")

        # Step 6: Verify IN series count
        cur.execute("""
            SELECT count(*), min(order_date), max(order_date), count(distinct invoice_number)
            FROM amazon_live_allocations
            WHERE company_id = 3 
              AND (warehouse_id = %s OR invoice_number ILIKE 'IN-%%' OR amazon_network_at_allocation = 'MFN')
        """, (wh_in_id,))
        res = cur.fetchone()
        print(f"\n--- VERIFICATION OF JSPL IN SERIES ---")
        print(f"Total IN series allocations in DB: {res[0]}")
        print(f"Order Date Min/Max: {res[1]} to {res[2]}")
        print(f"Unique Invoice Numbers: {res[3]}")

        cur.execute("""
            SELECT id, invoice_number, order_id, sku, order_date, invoice_date, warehouse_id
            FROM amazon_live_allocations
            WHERE company_id = 3 AND invoice_number ILIKE 'IN-%%'
            ORDER BY order_date DESC
            LIMIT 5
        """)
        print("\nSample IN series records:")
        for r in cur.fetchall():
            print(f"  ID: {r[0]} | Inv: {r[1]} | Order: {r[2]} | SKU: {r[3]} | OrderDate: {r[4]} | InvDate: {r[5]} | WH: {r[6]}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR during migration: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
