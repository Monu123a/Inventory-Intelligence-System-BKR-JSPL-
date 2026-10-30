import os
import sys
import argparse
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import dotenv_values

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
env_config = dotenv_values(ENV_PATH)
DATABASE_URL = env_config.get("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/transformation_engine"

DOWNLOADS_DIR = "/Users/harshahlawat/Downloads"
OCT_IN_PATH = os.path.join(DOWNLOADS_DIR, "IN SERIES OCTOBER.xlsx")
OCT_456_PATH = os.path.join(DOWNLOADS_DIR, "456.xlsx")
OCT_B2B_PATH = os.path.join(DOWNLOADS_DIR, "B2C & B2B JSPL OCTOBER.xlsx")
MASTER_MTR_PATH = os.path.join(DOWNLOADS_DIR, "Halte Amz Master GST Records 23 - 26 -3.xlsx")

FALLBACK_OCT_IN = "/Users/harshahlawat/.gemini/antigravity/brain/d247ab24-ed3f-44f6-936a-9d5c40d0c0be/.user_uploaded/media_1793273377560_a47053d3.xlsx"


def clean_str(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "null") else None


def clean_int(val, default=1):
    try:
        if pd.isna(val) or val is None:
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def clean_float(val):
    try:
        if pd.isna(val) or val is None:
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def clean_dt(val):
    if pd.isna(val) or val is None:
        return None
    try:
        dt = pd.to_datetime(val, dayfirst=True)
        return dt.to_pydatetime()
    except Exception:
        return None


def clean_hsn(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    try:
        f = float(s)
        return str(int(f))
    except Exception:
        return s


def deduce_warehouse_id(inv_num, wh_code_to_id, default_wh=14):
    if not inv_num:
        return default_wh
    inv_str = str(inv_num).strip().upper()
    
    # Check prefixes
    for code, wh_id in wh_code_to_id.items():
        if inv_str.startswith(f"{code}-"):
            return wh_id
            
    # Pure numeric invoices in VSHB file map to VSHB
    if inv_str.isdigit():
        return wh_code_to_id.get("VSHB", default_wh)
        
    return default_wh


def map_transaction_status(tx_type):
    if not tx_type:
        return "SHIPPED"
    t = str(tx_type).strip().lower()
    if t == "shipment":
        return "SHIPPED"
    elif t in ("refund", "return"):
        return "RETURNED"
    elif t in ("cancel", "cancelled", "freereplacement"):
        return "CANCELLED"
    return "SHIPPED"


def main():
    parser = argparse.ArgumentParser(description="Ingest Amazon MTR Records into database safely.")
    parser.add_argument("--dry-run", action="store_true", help="Perform parsing and comparison without DB commit.")
    parser.add_argument("--include-master", action="store_true", default=True, help="Include GST_MASTER_2026 sheet.")
    parser.add_argument("--sheet-year", type=str, default="2026", help="Master sheet year (default: 2026).")
    args = parser.parse_args()

    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Load Warehouses
    cur.execute("SELECT id, UPPER(code), company_id FROM warehouses WHERE status = 'ACTIVE';")
    wh_code_to_id = {}
    for wid, wcode, wcomp in cur.fetchall():
        if wcode:
            wh_code_to_id[wcode] = wid

    # Default fallbacks
    if "IN" not in wh_code_to_id:
        wh_code_to_id["IN"] = 38
    if "VSHB" not in wh_code_to_id:
        wh_code_to_id["VSHB"] = 14

    print(f"Loaded {len(wh_code_to_id)} warehouses.")

    # Load existing allocations for deduplication and matching
    print("Preloading existing allocations from database...")
    cur.execute("""
        SELECT id, order_id, sku, amazon_line_item_id, warehouse_id, status
        FROM amazon_live_allocations;
    """)
    existing_records = cur.fetchall()
    print(f"Found {len(existing_records)} existing allocations in DB.")

    db_by_order_sku = {}
    db_by_order_base_sku = {}
    db_by_line_item_id = {}

    for row in existing_records:
        rec_id, o_id, sku, line_id, wid, stat = row
        o_clean = (o_id or "").strip()
        s_clean = (sku or "").strip().upper()
        base_s = s_clean.split("-")[0]
        l_clean = (line_id or "").strip()

        if o_clean and s_clean:
            db_by_order_sku[(o_clean, s_clean)] = rec_id
        if o_clean and base_s:
            if (o_clean, base_s) not in db_by_order_base_sku:
                db_by_order_base_sku[(o_clean, base_s)] = rec_id
        if l_clean:
            db_by_line_item_id[l_clean] = rec_id

    # Collect datasets to ingest (ordered from oldest/broadest to most authoritative)
    dfs_to_process = []

    # 1. Master GST Sheet (Jan - Sep 2026)
    if args.include_master and os.path.exists(MASTER_MTR_PATH):
        sheet_name = f"GST_MASTER_{args.sheet_year}"
        print(f"Loading Master GST file sheet: {sheet_name} from {MASTER_MTR_PATH}...")
        df_master = pd.read_excel(MASTER_MTR_PATH, sheet_name=sheet_name)
        dfs_to_process.append((f"Master GST {args.sheet_year}", df_master, None, None))
    else:
        print(f"Warning: Master MTR file not found at {MASTER_MTR_PATH}")

    # 2. October B2C & B2B Master Report (All 15 FCs for October 2026)
    if os.path.exists(OCT_B2B_PATH):
        print(f"Loading October B2C & B2B Master Report: {OCT_B2B_PATH}")
        df_oct_b2b = pd.read_excel(OCT_B2B_PATH)
        dfs_to_process.append(("October B2C & B2B Master", df_oct_b2b, None, None))
    else:
        print(f"Warning: October B2C & B2B Master file not found at {OCT_B2B_PATH}")

    # 3. October VSHB Series (456.xlsx - 100% authoritative for VSHB)
    if os.path.exists(OCT_456_PATH):
        print(f"Loading October VSHB Series: {OCT_456_PATH}")
        df_oct_456 = pd.read_excel(OCT_456_PATH)
        dfs_to_process.append(("October VSHB Series (456.xlsx)", df_oct_456, 14, "VSHB"))

    # 4. October IN Series (Official company source of truth)
    oct_in_file = OCT_IN_PATH if os.path.exists(OCT_IN_PATH) else FALLBACK_OCT_IN
    if os.path.exists(oct_in_file):
        print(f"Loading October IN Series: {oct_in_file}")
        df_oct_in = pd.read_excel(oct_in_file)
        dfs_to_process.append(("October IN Series", df_oct_in, 38, "IN"))
    else:
        print(f"Warning: October IN file not found at {oct_in_file}")

    # Collect and unify records across datasets
    # Authoritative later datasets overwrite earlier datasets for the same (order_id, line_item_id)
    unified_records = {}
    ref_counts = {}

    for ds_name, df, forced_wh_id, default_series_prefix in dfs_to_process:
        print(f"\nProcessing {ds_name} with {len(df)} rows...")
        count = 0

        for _, row in df.iterrows():
            order_id = clean_str(row.get("Order Id"))
            sku = clean_str(row.get("Sku"))
            if not order_id or not sku:
                continue

            # Strict SKU Variant Isolation: preserve exact SKU variant
            sku_upper = sku.upper()
            base_sku = sku_upper.split("-")[0]

            raw_line_id = clean_str(row.get("Shipment Item Id"))
            if raw_line_id and "." in raw_line_id:
                try:
                    raw_line_id = str(int(float(raw_line_id)))
                except Exception:
                    pass

            if not raw_line_id:
                raw_line_id = f"MTR_{order_id}_{sku_upper}"

            tx_type = clean_str(row.get("Transaction Type"))
            status = map_transaction_status(tx_type)

            # Differentiate line item IDs by transaction type to prevent collisions and overwrites
            if tx_type == "Refund":
                cnt = ref_counts.get((order_id, raw_line_id), 0) + 1
                ref_counts[(order_id, raw_line_id)] = cnt
                line_item_id = f"{raw_line_id}_REF_{cnt}" if cnt > 1 else f"{raw_line_id}_REF"
            elif tx_type in ("Cancel", "Cancelled"):
                line_item_id = f"{raw_line_id}_CANCEL"
            elif tx_type == "FreeReplacement":
                line_item_id = raw_line_id
            else:
                line_item_id = raw_line_id

            inv_num = clean_str(row.get("Invoice Number"))
            if inv_num and inv_num.isdigit() and default_series_prefix:
                inv_num = f"{default_series_prefix}-{inv_num}"

            inv_date = clean_dt(row.get("Invoice Date"))
            ship_date = clean_dt(row.get("Shipment Date"))
            order_date = clean_dt(row.get("Order Date")) or inv_date

            # Fix any swapped day/month from master file using the canonical Month column
            month_col = row.get("Month")
            if pd.notna(month_col):
                try:
                    m_val = pd.to_datetime(month_col)
                    if ship_date and ship_date.month != m_val.month and ship_date.year == m_val.year:
                        try:
                            ship_date = ship_date.replace(month=m_val.month, day=ship_date.month)
                        except (ValueError, TypeError):
                            pass
                    if inv_date and inv_date.month != m_val.month and inv_date.year == m_val.year:
                        try:
                            inv_date = inv_date.replace(month=m_val.month, day=inv_date.month)
                        except (ValueError, TypeError):
                            pass
                    if order_date and order_date.month != m_val.month and order_date.year == m_val.year:
                        try:
                            order_date = order_date.replace(month=m_val.month, day=order_date.month)
                        except (ValueError, TypeError):
                            pass
                except Exception:
                    pass

            seller_gstin = clean_str(row.get("Seller Gstin")) or ""
            company_id = 2 if seller_gstin.startswith("04AEFPS") else 3

            # Determine Warehouse ID
            if forced_wh_id:
                warehouse_id = forced_wh_id
            else:
                warehouse_id = deduce_warehouse_id(inv_num, wh_code_to_id, default_wh=14)

            # Fulfillment Network
            f_channel = clean_str(row.get("Fulfillment Channel")) or ""
            is_mfn = (
                warehouse_id == 38 or
                (inv_num and inv_num.startswith("IN-")) or
                f_channel.upper() == "MFN"
            )
            amazon_network = "MFN" if is_mfn else "AFN"

            qty = clean_int(row.get("Quantity"), 1)
            gross_amt = clean_float(row.get("Tax Exclusive Gross"))
            tax_amt = clean_float(row.get("Total Tax Amount"))
            net_amt = clean_float(row.get("Invoice Amount"))

            # Fallback GST deduction if net is present but gross is missing
            if net_amt is not None and gross_amt is None:
                gst_pct = 18.0
                if "gst_rate" in row and pd.notna(row["gst_rate"]):
                    gst_pct = clean_float(row["gst_rate"]) or 18.0
                gross_amt = round(net_amt / (1.0 + (gst_pct / 100.0)), 2)
                tax_amt = round(net_amt - gross_amt, 2)

            buyer_name = clean_str(row.get("Buyer Name"))
            state_name = clean_str(row.get("Ship To State"))
            hsn_code = clean_hsn(row.get("Hsn/sac"))
            cust_gstin = clean_str(row.get("Customer Bill To Gstid")) or clean_str(row.get("Customer Ship To Gstid"))

            item_key = (order_id, line_item_id)
            unified_records[item_key] = {
                "company_id": company_id,
                "order_id": order_id,
                "line_item_id": line_item_id,
                "sku_upper": sku_upper,
                "base_sku": base_sku,
                "warehouse_id": warehouse_id,
                "amazon_network": amazon_network,
                "qty": qty,
                "status": status,
                "order_date": order_date,
                "inv_num": inv_num,
                "inv_date": inv_date,
                "ship_date": ship_date,
                "gross_amt": gross_amt,
                "tax_amt": tax_amt,
                "net_amt": net_amt,
                "buyer_name": buyer_name,
                "state_name": state_name,
                "hsn_code": hsn_code,
                "cust_gstin": cust_gstin,
                "ds_name": ds_name
            }
            count += 1

        print(f"Extracted {count} rows from {ds_name}.")

    to_insert = []
    to_update = []
    matched_db_ids = set()

    for item_key, item in unified_records.items():
        order_id = item["order_id"]
        line_item_id = item["line_item_id"]
        sku_upper = item["sku_upper"]
        base_sku = item["base_sku"]

        # Match against existing DB record
        matched_id = None
        if line_item_id in db_by_line_item_id:
            matched_id = db_by_line_item_id[line_item_id]
        elif item["status"] == "SHIPPED":
            if (order_id, sku_upper) in db_by_order_sku and db_by_order_sku[(order_id, sku_upper)] not in matched_db_ids:
                matched_id = db_by_order_sku[(order_id, sku_upper)]
            elif (order_id, base_sku) in db_by_order_base_sku and db_by_order_base_sku[(order_id, base_sku)] not in matched_db_ids:
                matched_id = db_by_order_base_sku[(order_id, base_sku)]

        if matched_id:
            matched_db_ids.add(matched_id)
            to_update.append((
                matched_id,
                sku_upper,
                line_item_id,
                item["warehouse_id"],
                item["amazon_network"],
                item["qty"],
                item["qty"],
                item["status"],
                True,
                item["order_date"],
                item["inv_num"],
                item["inv_date"],
                item["ship_date"],
                item["gross_amt"],
                item["tax_amt"],
                item["net_amt"],
                item["buyer_name"],
                item["state_name"],
                item["hsn_code"],
                item["cust_gstin"]
            ))
        else:
            to_insert.append((
                item["company_id"],
                order_id,
                line_item_id,
                sku_upper,
                item["warehouse_id"],
                item["amazon_network"],
                item["qty"],
                item["qty"],
                item["status"],
                True,
                item["order_date"],
                item["inv_num"],
                item["inv_date"],
                item["ship_date"],
                item["gross_amt"],
                item["tax_amt"],
                item["net_amt"],
                item["buyer_name"],
                item["state_name"],
                item["hsn_code"],
                item["cust_gstin"]
            ))

    print(f"\nSummary of planned actions:")
    print(f"- Records to UPDATE in amazon_live_allocations: {len(to_update)}")
    print(f"- Records to INSERT into amazon_live_allocations: {len(to_insert)}")

    # Handle cancelled orders for IN and FC series
    # Orders in DB for warehouse 38 or IN- prefix with UNSHIPPED/PENDING status that were not matched in MTR
    cur.execute("""
        SELECT id, order_id, sku, invoice_number 
        FROM amazon_live_allocations
        WHERE (warehouse_id = 38 OR invoice_number ILIKE 'IN-%')
          AND status IN ('UNSHIPPED', 'PENDING');
    """)
    unshipped_in = cur.fetchall()
    cancelled_ids = [r[0] for r in unshipped_in if r[0] not in matched_db_ids]
    print(f"- Identified {len(cancelled_ids)} unconfirmed/cancelled IN orders to mark as CANCELLED.")

    # Identify stale records in DB with date in October 2026 that were not in the official October MTR
    cur.execute("""
        SELECT id FROM amazon_live_allocations
        WHERE company_id = 3
          AND status = 'SHIPPED'
          AND COALESCE(shipment_date, invoice_date, order_date) >= '2026-10-01'
          AND COALESCE(shipment_date, invoice_date, order_date) <= '2026-10-31 23:59:59'
          AND NOT (id = ANY(%s));
    """, (list(matched_db_ids),))
    stale_oct_shipped = [r[0] for r in cur.fetchall()]
    print(f"- Identified {len(stale_oct_shipped)} stale October shipments to reset/cancel.")

    if args.dry_run:
        print("\n[DRY RUN COMPLETED] No changes were written to the database.")
        cur.close()
        conn.close()
        return

    # Execute Updates in Batches
    if to_update:
        print(f"\nExecuting batch update of {len(to_update)} records using execute_values...")
        update_query = """
            UPDATE amazon_live_allocations AS a
            SET
                sku = v.sku,
                amazon_line_item_id = v.amazon_line_item_id,
                warehouse_id = v.warehouse_id,
                amazon_network_at_allocation = v.amazon_network_at_allocation::"amazonnetworktype",
                allocated_qty = v.allocated_qty,
                reconciled_qty = v.reconciled_qty,
                status = v.status::"allocationstatus",
                closed = v.closed,
                order_date = v.order_date,
                invoice_number = v.invoice_number,
                invoice_date = v.invoice_date,
                shipment_date = v.shipment_date,
                gross_amount = v.gross_amount,
                tax_amount = v.tax_amount,
                net_amount = v.net_amount,
                party_name = v.party_name,
                state_name = v.state_name,
                hsn_code = v.hsn_code,
                customer_gstin = v.customer_gstin,
                updated_at = NOW()
            FROM (VALUES %s) AS v(
                id, sku, amazon_line_item_id, warehouse_id, amazon_network_at_allocation,
                allocated_qty, reconciled_qty, status, closed, order_date,
                invoice_number, invoice_date, shipment_date, gross_amount,
                tax_amount, net_amount, party_name, state_name, hsn_code, customer_gstin
            )
            WHERE a.id = v.id;
        """
        # Execute in chunks of 1000
        for i in range(0, len(to_update), 1000):
            chunk = to_update[i:i + 1000]
            execute_values(cur, update_query, chunk, page_size=1000)
            conn.commit()
            print(f"Updated {min(i + 1000, len(to_update))}/{len(to_update)} records...")

    # Execute Inserts in Batches
    if to_insert:
        print(f"\nExecuting batch insert of {len(to_insert)} records using execute_values...")
        insert_query = """
            INSERT INTO amazon_live_allocations (
                company_id, order_id, amazon_line_item_id, sku, warehouse_id,
                amazon_network_at_allocation, allocated_qty, reconciled_qty,
                status, closed, order_date, invoice_number, invoice_date,
                shipment_date, gross_amount, tax_amount, net_amount,
                party_name, state_name, hsn_code, customer_gstin,
                created_at, updated_at
            ) VALUES %s
            ON CONFLICT (order_id, sku, amazon_line_item_id)
            DO UPDATE SET
                warehouse_id = EXCLUDED.warehouse_id,
                amazon_network_at_allocation = EXCLUDED.amazon_network_at_allocation,
                allocated_qty = EXCLUDED.allocated_qty,
                reconciled_qty = EXCLUDED.reconciled_qty,
                status = EXCLUDED.status,
                closed = EXCLUDED.closed,
                order_date = EXCLUDED.order_date,
                invoice_number = EXCLUDED.invoice_number,
                invoice_date = EXCLUDED.invoice_date,
                shipment_date = EXCLUDED.shipment_date,
                gross_amount = EXCLUDED.gross_amount,
                tax_amount = EXCLUDED.tax_amount,
                net_amount = EXCLUDED.net_amount,
                party_name = EXCLUDED.party_name,
                state_name = EXCLUDED.state_name,
                hsn_code = EXCLUDED.hsn_code,
                customer_gstin = EXCLUDED.customer_gstin,
                updated_at = NOW();
        """
        insert_payload = [
            (
                r[0], r[1], r[2], r[3], r[4],
                r[5], r[6], r[7], r[8], r[9],
                r[10], r[11], r[12], r[13], r[14],
                r[15], r[16], r[17], r[18], r[19],
                r[20], pd.Timestamp.now().to_pydatetime(), pd.Timestamp.now().to_pydatetime()
            )
            for r in to_insert
        ]
        for i in range(0, len(insert_payload), 1000):
            chunk = insert_payload[i:i + 1000]
            execute_values(cur, insert_query, chunk, page_size=1000)
            conn.commit()
            print(f"Inserted {min(i + 1000, len(insert_payload))}/{len(insert_payload)} records...")

    # Mark cancelled orders
    if cancelled_ids:
        cur.execute("""
            UPDATE amazon_live_allocations
            SET status = 'CANCELLED', updated_at = NOW()
            WHERE id = ANY(%s);
        """, (cancelled_ids,))
        conn.commit()
        print(f"Marked {len(cancelled_ids)} unconfirmed orders as CANCELLED.")

    # Reset stale shipments
    if stale_oct_shipped:
        cur.execute("""
            UPDATE amazon_live_allocations
            SET status = 'CANCELLED', shipment_date = NULL, updated_at = NOW()
            WHERE id = ANY(%s);
        """, (stale_oct_shipped,))
        conn.commit()
        print(f"Reset and marked {len(stale_oct_shipped)} stale October records as CANCELLED.")

    print("\nSUCCESS: All Amazon MTR records ingested and synchronized!")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
