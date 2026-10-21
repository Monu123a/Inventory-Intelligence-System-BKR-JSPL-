import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def fix_product_nulls():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET min_stock_level = 0
        WHERE min_stock_level IS NULL;
    """)
    updated_min_stock = cur.rowcount

    cur.execute("""
        UPDATE products
        SET item_rate = 0.0
        WHERE item_rate IS NULL;
    """)
    updated_item_rate = cur.rowcount

    cur.execute("""
        UPDATE products
        SET reorder_level = 0
        WHERE reorder_level IS NULL AND sku = 'SERVICE CHARGE';
    """)
    updated_reorder = cur.rowcount

    cur.execute("""
        UPDATE products
        SET safety_stock = 0
        WHERE safety_stock IS NULL AND sku = 'SERVICE CHARGE';
    """)
    updated_safety = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    print(f"Updated min_stock_level: {updated_min_stock} records")
    print(f"Updated item_rate: {updated_item_rate} records")
    print(f"Updated reorder_level: {updated_reorder} records")
    print(f"Updated safety_stock: {updated_safety} records")

if __name__ == "__main__":
    fix_product_nulls()
