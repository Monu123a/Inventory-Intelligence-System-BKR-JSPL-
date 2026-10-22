import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv('backend/.env')
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in backend/.env")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        new_company_addr = "Plot no: 150, Industrial & Business Park-2,\nChandigarh-160002"
        new_warehouse_addr = "Plot no: 150, Industrial & Business Park-2, Chandigarh-160002"

        # 1. Update company_settings for JSPL (company_id = 3)
        cur.execute("""
            UPDATE company_settings 
            SET address = %s 
            WHERE company_id = 3
        """, (new_company_addr,))
        settings_count = cur.rowcount
        print(f"Updated company_settings records: {settings_count}")

        # 2. Update warehouses for JSPL (warehouses 14, 37, 38 or any with 24/9)
        cur.execute("""
            UPDATE warehouses 
            SET address = %s 
            WHERE company_id = 3 
              AND (id IN (14, 37, 38) OR address ILIKE %s)
        """, (new_warehouse_addr, '%24/9%'))
        wh_count = cur.rowcount
        print(f"Updated warehouses records: {wh_count}")

        # 3. Update existing sales snapshots for JSPL (company_id = 3) with 24/9
        cur.execute("""
            UPDATE sales 
            SET company_address_snapshot = %s 
            WHERE company_id = 3 
              AND company_address_snapshot ILIKE %s
        """, (new_company_addr, '%24/9%'))
        sales_count = cur.rowcount
        print(f"Updated sales records: {sales_count}")

        conn.commit()
        print("Transaction successfully committed.")
    except Exception as e:
        conn.rollback()
        print(f"Error during update: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
