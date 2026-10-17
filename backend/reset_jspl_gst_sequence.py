import os
import psycopg2
from dotenv import load_dotenv

def reset_sequence():
    load_dotenv('backend/.env')
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not found!")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # 1. Update cancelled sale 182 which had bill_number 'GST-529'
        cur.execute("""
            UPDATE sales
            SET 
                bill_number = 'CANCELLED-GST-529',
                invoice_number = 'CANCELLED-GST-529'
            WHERE id = 182 AND company_id = 3;
        """)
        sales_updated = cur.rowcount
        print(f"Updated cancelled sale 182: {sales_updated} row(s)")

        # 2. Reset or ensure document_sequences for JSPL (company_id=3) and GST prefix has last_number = 258
        cur.execute("""
            UPDATE document_sequences
            SET 
                last_number = 258,
                updated_at = NOW()
            WHERE company_id = 3 
              AND prefix = 'GST' 
              AND document_type = 'SALE';
        """)
        seq_updated = cur.rowcount
        print(f"Updated document_sequences for JSPL GST: {seq_updated} row(s)")

        conn.commit()
        print("Successfully committed sequence reset to 258 (next will be 259)!")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    reset_sequence()
