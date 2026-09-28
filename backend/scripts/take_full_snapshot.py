import psycopg2
import json
from datetime import datetime
from decimal import Decimal

def default_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, Decimal):
        return str(o)
    return str(o)

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'

def snapshot():
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
    """)
    tables = [r[0] for r in cur.fetchall()]
    
    snapshot_data = {}
    for table in tables:
        print(f"Dumping {table}...")
        cur.execute(f"SELECT * FROM {table};")
        rows = cur.fetchall()
        
        # Get column names
        colnames = [desc[0] for desc in cur.description]
        
        table_data = []
        for row in rows:
            table_data.append(dict(zip(colnames, row)))
        
        snapshot_data[table] = table_data
        
    filename = 'scratch/snapshot_pre_purchase.json'
    with open(filename, 'w') as f:
        json.dump(snapshot_data, f, default=default_converter)
        
    print(f"Full snapshot saved to {filename}")
    cur.close()
    conn.close()

if __name__ == '__main__':
    snapshot()
