#!/usr/bin/env python3
"""
Sync September 2026 IN-Series Amazon Allocations from Accountant Report
Source file: media_1793182489464_b6d8ea37.xlsx
"""

import os
import re
import sys
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 1. Resolve Database Connection
db_url = None
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.strip().split("=", 1)[1]
                break

if not db_url:
    db_url = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"

# 2. Source Accountant Report Path
EXCEL_PATH = "/Users/harshahlawat/.gemini/antigravity/brain/d247ab24-ed3f-44f6-936a-9d5c40d0c0be/.user_uploaded/media_1793182489464_b6d8ea37.xlsx"
if not os.path.exists(EXCEL_PATH):
    print(f"Error: Excel file not found at {EXCEL_PATH}")
    sys.exit(1)

# 3. Parse Excel Data
df = pd.read_excel(EXCEL_PATH, header=2)
bill_rows = df[df["SNO."].notnull() & (df["SNO."].astype(str) != "GRAND TOTALS")].copy()

def clean_sku(raw):
    raw = str(raw).strip()
    m = re.search(r'\b[A-Za-z]{2}\d{4}[0-9\-]*\b', raw)
    return m.group(0) if m else raw

orders_data = []
for _, r in bill_rows.iterrows():
    bdate_str = str(r["BILL DATE"]).strip()
    bdate = datetime.strptime(bdate_str, "%d/%m/%Y")
    sku = clean_sku(r["ITEM CODE"])
    bno = str(r["BILL NO."]).strip()
    oid = str(r["ORDER NO."]).strip()
    qty = int(r["SALE QUANTITY"])
    gross = float(r["GROSS AMOUNT"])
    net = float(r["NET AMOUNT"])
    igst = float(r["TOTAL IGST AMOUNT"]) if pd.notnull(r.get("TOTAL IGST AMOUNT")) else round(net - gross, 2)
    state = str(r["GST STATE NAME"]).replace("\xa0", " ").strip()
    party = str(r["PARTY NAME"]).strip()
    hsn = str(r["HSN CODE"]).replace(".0", "").strip() if pd.notnull(r.get("HSN CODE")) else ""
    
    orders_data.append({
        "bill_no": bno,
        "bill_date": bdate,
        "order_id": oid,
        "sku": sku,
        "qty": qty,
        "gross": gross,
        "net": net,
        "tax": igst,
        "party": party,
        "state": state,
        "hsn": hsn
    })

print(f"Parsed {len(orders_data)} orders from accountant report.")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

order_ids = [o["order_id"] for o in orders_data]
cur.execute("SELECT order_id, id, invoice_number, order_date FROM amazon_live_allocations WHERE order_id = ANY(%s);", (order_ids,))
existing_records = {r[0]: {"id": r[1], "inv": r[2], "date": r[3]} for r in cur.fetchall()}

to_update = []
to_insert = []

print("\n--- DRY-RUN SUMMARY ---")
for o in orders_data:
    oid = o["order_id"]
    if oid in existing_records:
        rec = existing_records[oid]
        to_update.append(o)
        print(f"[UPDATE] Order: {oid} | ID: {rec['id']} | Current Inv: {rec['inv']} -> New: {o['bill_no']} | Date: {o['bill_date'].strftime('%d/%m/%Y')}")
    else:
        to_insert.append(o)
        print(f"[INSERT] Order: {oid} | Bill: {o['bill_no']} | Date: {o['bill_date'].strftime('%d/%m/%Y')} | SKU: {o['sku']} | Net: {o['net']}")

print(f"\nTotal to Update: {len(to_update)}")
print(f"Total to Insert: {len(to_insert)}")
print(f"Total Combined: {len(to_update) + len(to_insert)} (Expected: 32)")

# 4. Perform Updates via execute_values
if to_update:
    update_tuples = [
        (
            o["bill_no"],
            o["bill_date"],
            o["bill_date"],
            o["bill_date"],
            o["gross"],
            o["tax"],
            o["net"],
            o["party"],
            o["state"],
            o["hsn"],
            38, # warehouse_id for IN
            3,  # company_id for JSPL
            o["order_id"]
        )
        for o in to_update
    ]
    update_query = """
        UPDATE amazon_live_allocations AS a
        SET invoice_number = v.bill_no,
            order_date = v.order_date::timestamp,
            invoice_date = v.invoice_date::timestamp,
            updated_at = v.updated_at::timestamp,
            gross_amount = v.gross_amount::numeric,
            tax_amount = v.tax_amount::numeric,
            net_amount = v.net_amount::numeric,
            party_name = v.party_name,
            state_name = v.state_name,
            hsn_code = v.hsn_code,
            warehouse_id = v.warehouse_id::int,
            company_id = v.company_id::int
        FROM (VALUES %s) AS v(bill_no, order_date, invoice_date, updated_at, gross_amount, tax_amount, net_amount, party_name, state_name, hsn_code, warehouse_id, company_id, order_id)
        WHERE a.order_id = v.order_id;
    """
    execute_values(cur, update_query, update_tuples, template=None, page_size=100)
    print(f"\nSuccessfully updated {len(to_update)} existing allocation records.")

# 5. Perform Inserts via execute_values
if to_insert:
    insert_tuples = [
        (
            3,  # company_id
            o["order_id"],
            f"default-{o['order_id'][-6:]}", # line_item_id
            o["sku"],
            38, # warehouse_id
            "MFN", # amazon_network_at_allocation
            o["qty"],
            o["qty"],
            "SHIPPED", # status
            False, # closed
            o["bill_date"],
            o["bill_date"],
            o["bill_no"],
            o["bill_date"],
            o["bill_date"],
            o["gross"],
            o["tax"],
            o["net"],
            o["party"],
            o["state"],
            o["hsn"]
        )
        for o in to_insert
    ]
    insert_query = """
        INSERT INTO amazon_live_allocations (
            company_id, order_id, amazon_line_item_id, sku,
            warehouse_id, amazon_network_at_allocation, allocated_qty,
            reconciled_qty, status, closed, order_date, invoice_date,
            invoice_number, created_at, updated_at,
            gross_amount, tax_amount, net_amount,
            party_name, state_name, hsn_code
        ) VALUES %s
        ON CONFLICT (order_id, sku, amazon_line_item_id) DO UPDATE SET
            invoice_number = EXCLUDED.invoice_number,
            order_date = EXCLUDED.order_date,
            invoice_date = EXCLUDED.invoice_date,
            gross_amount = EXCLUDED.gross_amount,
            tax_amount = EXCLUDED.tax_amount,
            net_amount = EXCLUDED.net_amount,
            party_name = EXCLUDED.party_name,
            state_name = EXCLUDED.state_name,
            hsn_code = EXCLUDED.hsn_code,
            warehouse_id = EXCLUDED.warehouse_id,
            company_id = EXCLUDED.company_id;
    """
    execute_values(cur, insert_query, insert_tuples, template=None, page_size=100)
    print(f"Successfully inserted {len(to_insert)} missing allocation records.")

conn.commit()

# 6. Verification Query
cur.execute("""
    SELECT count(*), sum(allocated_qty), sum(gross_amount), sum(net_amount), min(invoice_number), max(invoice_number)
    FROM amazon_live_allocations
    WHERE warehouse_id = 38
      AND order_date >= '2026-09-01'
      AND order_date <= '2026-09-30 23:59:59';
""")
stats = cur.fetchone()
print("\n=== POST-SYNC VERIFICATION FOR SEPTEMBER 2026 IN SERIES ===")
print(f"Total Records: {stats[0]} (Expected: 32)")
print(f"Total Qty:     {stats[1]} (Expected: 32)")
print(f"Total Gross:   {stats[2]} (Expected: 299170.16)")
print(f"Total Net:     {stats[3]} (Expected: 328686.00)")
print(f"Invoice Range: {stats[4]} to {stats[5]} (Expected: IN-488 to IN-525)")

cur.close()
conn.close()
print("Sync script completed successfully.")
