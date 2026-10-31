import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
env_config = dotenv_values(ENV_PATH)
DATABASE_URL = env_config.get("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/transformation_engine"

def sync_mfn_returns():
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Query all MFN returns from amazon_live_allocations
    query = """
        SELECT 
            a.company_id,
            COALESCE('MFN-' || NULLIF(a.invoice_number, ''), 'MFN-' || a.order_id) AS amazon_return_id,
            a.order_id AS amazon_order_id,
            a.amazon_line_item_id AS order_item_id,
            a.sku,
            NULL::character varying AS asin,
            COALESCE(p.name, a.sku) AS product_name,
            GREATEST(ABS(COALESCE(a.allocated_qty, 1)), 1) AS quantity,
            'MFN Customer Return (' || COALESCE(a.invoice_number, 'IN') || ')' AS return_reason,
            'Received' AS return_status,
            COALESCE(a.order_date, a.shipment_date) AS requested_at,
            COALESCE(a.shipment_date, a.order_date) AS received_at,
            NOW() AS last_synced_at,
            NOW() AS created_at,
            NOW() AS updated_at
        FROM amazon_live_allocations a
        LEFT JOIN products p ON p.sku = a.sku AND p.company_id = a.company_id
        WHERE a.status = 'RETURNED'
          AND (
              a.amazon_network_at_allocation = 'MFN' 
              OR a.warehouse_id = 38 
              OR a.invoice_number ILIKE 'IN-%'
          );
    """
    cur.execute(query)
    mfn_records = cur.fetchall()
    print(f"Found {len(mfn_records)} MFN return records in amazon_live_allocations.")

    if not mfn_records:
        print("No MFN return records found to sync.")
        cur.close()
        conn.close()
        return

    insert_query = """
        INSERT INTO amazon_returns (
            company_id, amazon_return_id, amazon_order_id, order_item_id,
            sku, asin, product_name, quantity, return_reason,
            return_status, requested_at, received_at, last_synced_at,
            created_at, updated_at
        ) VALUES %s
        ON CONFLICT (company_id, amazon_return_id, order_item_id)
        DO UPDATE SET
            amazon_order_id = EXCLUDED.amazon_order_id,
            sku = EXCLUDED.sku,
            asin = COALESCE(EXCLUDED.asin, amazon_returns.asin),
            product_name = COALESCE(EXCLUDED.product_name, amazon_returns.product_name),
            quantity = EXCLUDED.quantity,
            return_reason = EXCLUDED.return_reason,
            return_status = EXCLUDED.return_status,
            received_at = COALESCE(EXCLUDED.received_at, amazon_returns.received_at),
            last_synced_at = NOW(),
            updated_at = NOW();
    """

    execute_values(cur, insert_query, mfn_records, page_size=500)
    conn.commit()
    print(f"Successfully synced {len(mfn_records)} MFN return records into amazon_returns.")

    cur.execute("SELECT count(*) FROM amazon_returns WHERE amazon_return_id LIKE 'MFN-%';")
    mfn_in_db = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM amazon_returns;")
    total_in_db = cur.fetchone()[0]
    print(f"Current amazon_returns table status: {mfn_in_db} MFN returns out of {total_in_db} total returns.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    sync_mfn_returns()
