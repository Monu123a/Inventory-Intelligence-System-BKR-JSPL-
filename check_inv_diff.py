import sys
import os
import json
import psycopg2

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'

def check():
    with open('scratch/snapshot_1233.json', 'r') as f:
        snapshot = json.load(f)
    
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT id, current_qty FROM inventory WHERE id IN (1818, 1819, 1820)")
    db_rows = cur.fetchall()
    
    print("From DB:", db_rows)
    
    snap_rows = [x for x in snapshot['inventory'] if x['id'] in [1818, 1819, 1820]]
    print("From Snapshot:", [(x['id'], x['current_qty']) for x in snap_rows])

if __name__ == '__main__':
    check()
