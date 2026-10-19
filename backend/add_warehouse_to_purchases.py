import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Load database URL from backend/.env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://postgres.ttlxrvjydjhpltdotnml:xakket-famqec-7Mysto@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres'
)

def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        # 1. Add warehouse_id column if not exists
        print("Checking if warehouse_id column exists on purchases...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'purchases' AND column_name = 'warehouse_id';
        """)
        exists = cur.fetchone()
        if not exists:
            print("Adding warehouse_id column to purchases table...")
            cur.execute("""
                ALTER TABLE purchases 
                ADD COLUMN warehouse_id INTEGER REFERENCES warehouses(id);
            """)
            print("Column warehouse_id added.")
        else:
            print("Column warehouse_id already exists.")

        # 2. Backfill warehouse_id from inventory_movements
        print("Backfilling warehouse_id from inventory_movements...")
        cur.execute("""
            UPDATE purchases p
            SET warehouse_id = sub.warehouse_id
            FROM (
                SELECT DISTINCT ON (reference_id) reference_id, warehouse_id
                FROM inventory_movements
                WHERE source = 'PURCHASE' AND warehouse_id IS NOT NULL
                ORDER BY reference_id, id DESC
            ) sub
            WHERE (sub.reference_id = p.invoice_number OR sub.reference_id = 'PUR-' || p.id)
              AND p.warehouse_id IS NULL;
        """)
        updated_from_movements = cur.rowcount
        print(f"Updated {updated_from_movements} purchases with warehouse_id from inventory movements.")

        # 3. For any remaining purchases, backfill using default warehouse for the company
        cur.execute("""
            UPDATE purchases
            SET warehouse_id = 14
            WHERE company_id = 3 AND warehouse_id IS NULL;
        """)
        updated_jspl = cur.rowcount
        print(f"Updated {updated_jspl} JSPL purchases with default Central warehouse (14).")

        cur.execute("""
            UPDATE purchases
            SET warehouse_id = 39
            WHERE company_id = 2 AND warehouse_id IS NULL;
        """)
        updated_bkr = cur.rowcount
        print(f"Updated {updated_bkr} BKR purchases with default BKR Central warehouse (39).")

        conn.commit()
        print("Transaction successfully committed.")

        # 4. Verify purchases
        cur.execute("""
            SELECT id, company_id, invoice_number, warehouse_id, status 
            FROM purchases 
            ORDER BY id DESC LIMIT 10;
        """)
        print("\nVerification of latest 10 purchases:")
        for row in cur.fetchall():
            print(row)

    except Exception as e:
        conn.rollback()
        print("Error during migration, rolled back:", e)
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
