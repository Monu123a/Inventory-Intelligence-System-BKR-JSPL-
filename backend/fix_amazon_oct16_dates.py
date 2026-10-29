#!/usr/bin/env python3
"""
Fix Amazon allocations that were stamped with the sync execution timestamp (2026-10-16 09:10:26)
instead of their actual Amazon PurchaseDate.

Follows AGENTS.md database update guidelines:
- Runs in backend/
- Uses centralized DATABASE_URL from .env
- Uses raw psycopg2 and psycopg2.extras.execute_values for bulk update
- Commits transaction and prints updated count
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# Load environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment!")

from sp_api.api import Orders
from sp_api.base import Marketplaces

credentials = dict(
    refresh_token=os.getenv("LWA_REFRESH_TOKEN"),
    lwa_app_id=os.getenv("LWA_CLIENT_ID"),
    lwa_client_secret=os.getenv("LWA_CLIENT_SECRET"),
    aws_secret_key=os.getenv("AWS_SECRET_KEY"),
    aws_access_key=os.getenv("AWS_ACCESS_KEY"),
    role_arn=os.getenv("AWS_IAM_ROLE_ARN"),
)
marketplace = getattr(Marketplaces, os.getenv("MARKETPLACE_ID", "IN"), Marketplaces.IN)
orders_api = Orders(credentials=credentials, marketplace=marketplace)

def main():
    print("--- Connecting to Database ---")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Find allocations with the batch sync timestamp
    cur.execute("""
        SELECT id, order_id, sku, invoice_number, order_date
        FROM amazon_live_allocations
        WHERE order_date >= '2026-10-16 09:10:00'
          AND order_date <= '2026-10-16 09:11:00'
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} allocation records needing date correction.")

    unique_orders = sorted(list(set(r[1] for r in rows if r[1])))
    print(f"Total unique Amazon Orders to query: {len(unique_orders)}")

    order_dates = {}
    errors = 0

    print("Fetching true PurchaseDate from Amazon SP-API...")
    for idx, order_id in enumerate(unique_orders, 1):
        retries = 4
        success = False
        for attempt in range(retries):
            try:
                res = orders_api.get_order(order_id)
                payload = res.payload or {}
                purchase_date_str = payload.get("PurchaseDate")
                if purchase_date_str:
                    # e.g. '2026-08-15T04:18:10Z'
                    dt = datetime.fromisoformat(purchase_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    order_dates[order_id] = dt
                    success = True
                    break
                else:
                    print(f"[{idx}/{len(unique_orders)}] {order_id} - No PurchaseDate in payload")
                    break
            except Exception as e:
                err_str = str(e)
                if "TooManyRequests" in err_str or "QuotaExceeded" in err_str or "429" in err_str:
                    wait_sec = 2 ** (attempt + 1)
                    time.sleep(wait_sec)
                    continue
                else:
                    print(f"[{idx}/{len(unique_orders)}] Error for {order_id}: {e}")
                    errors += 1
                    break

        if success and idx % 10 == 0:
            print(f"  Processed {idx}/{len(unique_orders)} orders (Latest: {order_id} -> {order_dates.get(order_id)})...")

        # Respect SP-API Orders rate limit (1 req/sec)
        time.sleep(0.6)

    print(f"\nFetched real dates for {len(order_dates)}/{len(unique_orders)} orders. Errors: {errors}")

    if not order_dates:
        print("No order dates resolved. Exiting.")
        return

    # Build updates for allocations
    update_data = []
    for r in rows:
        alloc_id, order_id, sku, inv_num, current_dt = r
        if order_id in order_dates:
            real_dt = order_dates[order_id]
            update_data.append((real_dt, real_dt, alloc_id))

    print(f"\nPrepared {len(update_data)} allocation rows for bulk update.")

    # Perform bulk update with execute_values
    update_query = """
        UPDATE amazon_live_allocations AS a
        SET order_date = v.order_date,
            invoice_date = v.invoice_date
        FROM (VALUES %s) AS v(order_date, invoice_date, id)
        WHERE a.id = v.id;
    """
    execute_values(cur, update_query, update_data, template="(%s, %s, %s)")
    conn.commit()

    print(f"SUCCESS: Successfully committed transaction! Updated {len(update_data)} records in amazon_live_allocations.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
