import psycopg2
import json

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'

def check():
    with open('scratch/snapshot_1233.json', 'r') as f:
        snapshot = json.load(f)
    
    snap_ids = set([x['id'] for x in snapshot['inventory']])
    
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM inventory")
    db_ids = set([r[0] for r in cur.fetchall()])
    
    extra = db_ids - snap_ids
    print(f"Extra inventory IDs in DB: {len(extra)}")
    if extra:
        print("First few extra:", list(extra)[:10])

if __name__ == '__main__':
    check()
