import psycopg2
import json

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'

def fix():
    with open('scratch/snapshot_1233.json', 'r') as f:
        snapshot = json.load(f)
    
    snap_ids = tuple([x['id'] for x in snapshot['inventory']])
    
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM inventory WHERE id NOT IN %s", (snap_ids,))
    print(f"Deleted {cur.rowcount} extra inventory rows!")
    
    conn.commit()
    cur.close()
    conn.close()

if __name__ == '__main__':
    fix()
