import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

bkr_bank_details = {
    "account_name": "B.K. RAMAN & CO (CA)",
    "account_no": "41836801381",
    "ifsc": "SBIN0007501",
    "bank_name": "State Bank Of India",
    "branch": "Industrial Area, Phase-2",
    "city": "Chandigarh"
}

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

try:
    # 1. Update company_settings for BKR (company_id = 2)
    cur.execute(
        """
        UPDATE company_settings 
        SET bank_details = %s
        WHERE company_id = 2
        """,
        (json.dumps(bkr_bank_details),)
    )
    settings_updated = cur.rowcount

    # 2. Update company_bank_details_snapshot for all BKR sales (company_id = 2)
    cur.execute(
        """
        UPDATE sales 
        SET company_bank_details_snapshot = %s
        WHERE company_id = 2
        """,
        (json.dumps(bkr_bank_details),)
    )
    sales_updated = cur.rowcount

    conn.commit()
    print(f"Successfully updated company_settings: {settings_updated} record(s)")
    print(f"Successfully updated sales bank details snapshot: {sales_updated} record(s)")

except Exception as e:
    conn.rollback()
    print(f"Error during bank details update: {e}")
    raise
finally:
    cur.close()
    conn.close()
