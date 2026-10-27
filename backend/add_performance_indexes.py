import os
import sys
import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

INDEXES = [
    # sale_items
    ("idx_sale_items_sale_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_items_sale_id ON sale_items (sale_id);"),
    ("idx_sale_items_product_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sale_items_product_id ON sale_items (product_id);"),
    
    # sales
    ("idx_sales_company_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_company_created ON sales (company_id, created_at DESC);"),
    ("idx_sales_sale_date", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_sale_date ON sales (company_id, sale_date DESC);"),
    
    # fc_dispatches
    ("idx_fc_dispatches_company_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fc_dispatches_company_created ON fc_dispatches (company_id, created_at DESC);"),
    ("idx_fc_dispatches_warehouse", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fc_dispatches_warehouse ON fc_dispatches (warehouse_id);"),
    
    # inventory
    ("idx_inventory_warehouse_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_warehouse_id ON inventory (warehouse_id);"),
    ("idx_inventory_product_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_id ON inventory (product_id);"),
    
    # inventory_movements
    ("idx_inventory_movements_sku_wh", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_movements_sku_wh ON inventory_movements (product_sku, warehouse_id);"),
    ("idx_inventory_movements_company_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_movements_company_created ON inventory_movements (company_id, created_at DESC);"),
    
    # audit_logs
    ("idx_audit_logs_company_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_company_created ON audit_logs (company_id, created_at DESC);"),
    ("idx_audit_logs_entity", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_entity ON audit_logs (entity_type, entity_id);"),
    
    # delivery_challans
    ("idx_delivery_challans_sale_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_challans_sale_id ON delivery_challans (sale_id);"),
    ("idx_delivery_challans_company_created", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_challans_company_created ON delivery_challans (company_id, created_at DESC);"),
]

def add_indexes():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True  # CONCURRENTLY requires autocommit
    cur = conn.cursor()

    print("Adding performance indexes to PostgreSQL...")
    created_count = 0
    for name, sql in INDEXES:
        try:
            cur.execute(sql)
            print(f"  ✓ {name}")
            created_count += 1
        except Exception as e:
            print(f"  ✗ {name} failed: {e}")

    cur.close()
    conn.close()
    print(f"\nDone! Processed {created_count} indexes.")

if __name__ == '__main__':
    add_indexes()
