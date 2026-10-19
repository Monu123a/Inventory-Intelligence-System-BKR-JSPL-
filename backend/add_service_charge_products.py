import os
from dotenv import load_dotenv
import psycopg2

def main():
    load_dotenv('backend/.env')
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found in environment.")
        return

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    cur.execute("SELECT id, code, name FROM companies;")
    companies = cur.fetchall()
    print("Existing companies:", companies)

    inserted_count = 0
    for comp_id, comp_code, comp_name in companies:
        cur.execute("""
            SELECT id FROM products 
            WHERE company_id = %s AND sku = 'SERVICE CHARGE';
        """, (comp_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO products (
                    company_id, sku, name, category, brand, 
                    hsn, hsn_code, default_gst_rate, unit, status, item_rate
                ) VALUES (
                    %s, 'SERVICE CHARGE', 'SERVICE CHARGE', 'SERV', 'SERVICE',
                    '9987', '9987', 18.0, 'SERV', 'Active', 0.0
                ) RETURNING id;
            """, (comp_id,))
            new_id = cur.fetchone()[0]
            print(f"Created SERVICE CHARGE product for company {comp_code} (ID: {comp_id}) -> Product ID: {new_id}")
            inserted_count += 1
        else:
            print(f"SERVICE CHARGE product already exists for company {comp_code} (ID: {comp_id}) -> Product ID: {row[0]}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully committed. Total new records inserted: {inserted_count}")

if __name__ == '__main__':
    main()
