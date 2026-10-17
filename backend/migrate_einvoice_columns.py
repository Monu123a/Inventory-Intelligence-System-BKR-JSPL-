import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
CENTRAL_DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
DATABASE_URL = os.environ.get("DATABASE_URL") or CENTRAL_DATABASE_URL

def migrate():
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        # 1. Update company_settings
        print("Checking company_settings table...")
        cur.execute("""
            ALTER TABLE company_settings
            ADD COLUMN IF NOT EXISTS einvoice_enabled BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS einvoice_provider VARCHAR DEFAULT 'CLEARTAX',
            ADD COLUMN IF NOT EXISTS einvoice_config JSON DEFAULT '{}'::json;
        """)

        # 2. Update sales
        print("Checking sales table...")
        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS einvoice_status VARCHAR DEFAULT 'NOT_GENERATED',
            ADD COLUMN IF NOT EXISTS einvoice_error_message TEXT,
            ADD COLUMN IF NOT EXISTS einvoice_canceled_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS einvoice_cancel_reason VARCHAR;
        """)

        # 3. If any sale already has einvoice_irn, update its status to GENERATED
        cur.execute("""
            UPDATE sales 
            SET einvoice_status = 'GENERATED' 
            WHERE einvoice_irn IS NOT NULL AND einvoice_status = 'NOT_GENERATED';
        """)

        conn.commit()
        print("✅ E-Invoice database migration completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
