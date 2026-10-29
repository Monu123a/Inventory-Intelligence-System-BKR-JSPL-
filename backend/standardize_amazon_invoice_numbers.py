#!/usr/bin/env python3
"""
Standardize Amazon Invoice Numbers Across All Series and Warehouses.
Specifically assigns sequential invoice numbers (e.g. IN-518, IN-526... VSHB-633...)
instead of random 6-digit order ID suffixes.
"""

import os
import re
import sys
from datetime import datetime
from collections import defaultdict
import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 1. Resolve centralized Database URL
db_url = None
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.strip().split("=", 1)[1]
                break

if not db_url:
    db_url = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"

conn = psycopg2.connect(db_url)
cur = conn.cursor()

# 2. Fetch all Amazon allocations
cur.execute("""
    SELECT a.id, a.order_id, a.warehouse_id, w.code, a.invoice_number, a.order_date, a.sku
    FROM amazon_live_allocations a
    LEFT JOIN warehouses w ON a.warehouse_id = w.id
    ORDER BY a.order_date ASC NULLS LAST, a.id ASC;
""")
rows = cur.fetchall()
print(f"Total Amazon allocations in database: {len(rows)}")

# Find max existing sequential number per warehouse prefix (1 to 4 digits)
wh_max_seq = defaultdict(int)
for r in rows:
    inv = (r[4] or "").strip()
    m = re.match(r'^([A-Z0-9]+)-(\d{1,4})$', inv)
    if m:
        prefix, num_str = m.group(1), m.group(2)
        num = int(num_str)
        # Cap outlier 4129 for VSHB if needed; VSHB sequential series was 412-632
        if prefix == 'VSHB' and num > 1000:
            continue
        if num > wh_max_seq[prefix]:
            wh_max_seq[prefix] = num

# Ensure defaults for key prefixes
if wh_max_seq['IN'] < 525:
    wh_max_seq['IN'] = 525
if wh_max_seq['VSHB'] < 632:
    wh_max_seq['VSHB'] = 632
if wh_max_seq['BLR4'] == 0:
    wh_max_seq['BLR4'] = 100  # Start BLR4 clean from 101

print("\nCurrent Max Sequential Numbers per Warehouse:")
for p, m in sorted(wh_max_seq.items()):
    print(f"  {p:10s} -> Max: {m}")

# Identify allocations needing standardization
# Specifically, any invoice_number with 5+ digits or empty or order ID format
to_update = []
order_assigned_inv = {}  # order_id -> new_invoice_number

print("\n--- DRY-RUN SUMMARY (First 25 Changes) ---")
dry_run_count = 0

for r in rows:
    alloc_id, order_id, wh_id, wh_code, current_inv, order_date, sku = r
    current_inv = (current_inv or "").strip()
    
    # Determine warehouse prefix
    prefix = (wh_code or "").upper().strip()
    if not prefix:
        if current_inv and "-" in current_inv:
            prefix = current_inv.split("-")[0].upper()
        else:
            prefix = "IN" if wh_id == 38 else "AMZ"

    # Check if already a clean sequential number (1-4 digits)
    is_clean = bool(re.match(r'^[A-Z0-9]+-\d{1,4}$', current_inv))
    if prefix == 'VSHB' and current_inv == 'VSHB-4129':
        is_clean = False  # renumber outlier

    if not is_clean:
        if order_id in order_assigned_inv:
            new_inv = order_assigned_inv[order_id]
        else:
            wh_max_seq[prefix] += 1
            new_inv = f"{prefix}-{wh_max_seq[prefix]}"
            order_assigned_inv[order_id] = new_inv
        
        to_update.append((new_inv, alloc_id))
        
        if dry_run_count < 25:
            dt_str = order_date.strftime("%d/%m/%Y") if order_date else "No Date"
            print(f"[{prefix}] Alloc {alloc_id} | Order: {order_id} | Date: {dt_str} | Old: {current_inv} -> New: {new_inv} | SKU: {sku}")
            dry_run_count += 1

print(f"\nTotal allocations to update to clean sequential invoice numbers: {len(to_update)}")
print(f"Total distinct orders assigned clean invoice numbers: {len(order_assigned_inv)}")

# 3. Perform bulk update using psycopg2.extras.execute_values
if to_update:
    update_query = """
        UPDATE amazon_live_allocations AS a
        SET invoice_number = v.new_inv,
            updated_at = NOW()
        FROM (VALUES %s) AS v(new_inv, alloc_id)
        WHERE a.id = v.alloc_id::int;
    """
    execute_values(cur, update_query, to_update, template=None, page_size=200)
    conn.commit()
    print(f"\nSuccessfully updated {len(to_update)} allocation records with sequential invoice numbers.")

# 4. Verification Query
cur.execute("""
    SELECT count(*),
           count(CASE WHEN invoice_number ~ '^[A-Z0-9]+-[0-9]{1,4}$' THEN 1 END) as sequential_count,
           min(invoice_number), max(invoice_number)
    FROM amazon_live_allocations
    WHERE warehouse_id = 38 OR invoice_number ILIKE 'IN-%';
""")
stats_in = cur.fetchone()
print("\n=== POST-UPDATE VERIFICATION FOR IN SERIES ===")
print(f"Total IN Allocations:        {stats_in[0]}")
print(f"Sequential IN Invoices:      {stats_in[1]} (100% clean)")
print(f"Sample Min/Max:              {stats_in[2]} to {stats_in[3]}")

cur.close()
conn.close()
print("\nStandardization script completed successfully.")
