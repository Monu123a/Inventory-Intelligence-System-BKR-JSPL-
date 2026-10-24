import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Connect using raw psycopg2
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # Query current settings
            cur.execute("""
                SELECT cs.company_id, c.code, c.name, cs.amazon_sync_enabled, cs.amazon_returns_sync_enabled
                FROM company_settings cs
                JOIN companies c ON cs.company_id = c.id
                ORDER BY cs.company_id;
            """)
            rows = cur.fetchall()
            print("Current Company Settings:")
            for row in rows:
                print(f"Company ID: {row[0]}, Code: {row[1]}, Name: {row[2]}, amazon_sync_enabled: {row[3]}, amazon_returns_sync_enabled: {row[4]}")

            # Update company_id = 3 (JSPL) to enable both sync flags
            cur.execute("""
                UPDATE company_settings
                SET amazon_sync_enabled = TRUE,
                    amazon_returns_sync_enabled = TRUE
                WHERE company_id = 3;
            """)
            updated_count = cur.rowcount
            conn.commit()
            print(f"Successfully updated records: {updated_count}")

            # Verify updated row
            cur.execute("""
                SELECT cs.company_id, c.code, c.name, cs.amazon_sync_enabled, cs.amazon_returns_sync_enabled
                FROM company_settings cs
                JOIN companies c ON cs.company_id = c.id
                WHERE cs.company_id = 3;
            """)
            verified = cur.fetchone()
            print(f"Verified Company {verified[0]} ({verified[1]}): amazon_sync_enabled={verified[3]}, amazon_returns_sync_enabled={verified[4]}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
