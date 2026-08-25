import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

RENDER_POSTGRES_URL = os.getenv('DATABASE_URL', 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg')

def run_migration():
    print("Starting Purchases Module DB Migration...")
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()

    try:
        # 1. Create Vendors
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                contact VARCHAR(255),
                payable_balance NUMERIC(15, 2) DEFAULT 0.00,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Create Purchases
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER NOT NULL REFERENCES vendors(id),
                company_id INTEGER NOT NULL REFERENCES companies(id),
                operator_id INTEGER NOT NULL REFERENCES users(id),
                status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
                invoice_number VARCHAR(100),
                total_amount NUMERIC(15, 2) DEFAULT 0.00,
                idempotency_key VARCHAR(255) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                received_at TIMESTAMP WITHOUT TIME ZONE,
                
                -- Unique constraints specific to company isolation
                CONSTRAINT uix_company_invoice_number UNIQUE (company_id, invoice_number),
                CONSTRAINT uix_company_idempotency_key UNIQUE (company_id, idempotency_key)
            );
        """)

        # 3. Create Purchase Items
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchase_items (
                id SERIAL PRIMARY KEY,
                purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id),
                product_sku VARCHAR(100) NOT NULL,
                description TEXT,
                qty NUMERIC(15, 2) NOT NULL DEFAULT 1.00,
                unit_cost NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                gst_pct NUMERIC(5, 2) DEFAULT 0.00,
                hsn VARCHAR(50),
                line_total NUMERIC(15, 2) NOT NULL DEFAULT 0.00
            );
        """)

        # 4. Create Offline Purchases
        cur.execute("""
            CREATE TABLE IF NOT EXISTS offline_purchases (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                operator_id INTEGER NOT NULL REFERENCES users(id),
                payload JSONB NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                idempotency_key VARCHAR(255) NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP WITHOUT TIME ZONE,
                purchase_id INTEGER REFERENCES purchases(id),
                
                CONSTRAINT uix_offline_company_idempotency UNIQUE (company_id, idempotency_key)
            );
        """)

        # 5. Add Explicit Indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS ix_purchase_items_sku ON purchase_items(product_sku);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_purchases_status ON purchases(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_offline_purchases_status ON offline_purchases(status);")

        conn.commit()
        print("Migration complete! Tables created successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
