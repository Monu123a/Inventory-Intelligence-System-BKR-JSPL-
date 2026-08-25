import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Use the environment variable if available, else fallback to the known live URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg")

def upgrade_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("Adding payment tracking columns to purchases...")
        cur.execute("ALTER TABLE purchases ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'UNPAID';")
        cur.execute("ALTER TABLE purchases ADD COLUMN IF NOT EXISTS amount_paid NUMERIC(15,2) DEFAULT 0.0;")
        cur.execute("ALTER TABLE purchases ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);")
        
        print("Creating vendor_transactions ledger table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendor_transactions (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER NOT NULL REFERENCES vendors(id),
                transaction_type VARCHAR(50) NOT NULL, -- 'INVOICE' or 'PAYMENT'
                amount NUMERIC(15,2) NOT NULL,
                ref_purchase_id INTEGER REFERENCES purchases(id),
                txn_ref VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
            );
        """)
        
        # Ensure unique invoice numbers per company
        # We already handled this earlier, but good to ensure
        
        print("Committing changes...")
        conn.commit()
        print("Database upgrade successful.")
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"Error during upgrade: {e}")
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    upgrade_db()
