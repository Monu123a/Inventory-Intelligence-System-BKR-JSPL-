import sys
import os
import json
import psycopg2
from psycopg2.extras import execute_values

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'

def restore():
    print('Restoring inventory quantities from snapshot 1233 using raw psycopg2...')
    with open('scratch/snapshot_1233.json', 'r') as f:
        snapshot = json.load(f)
    
    update_data = []
    for data in snapshot['inventory']:
        update_data.append((
            data['current_qty'],
            data['available_qty'],
            data['reserved_qty'],
            data['id']
        ))
        
    conn = psycopg2.connect(RENDER_POSTGRES_URL)
    cur = conn.cursor()
    
    query = """
        UPDATE inventory AS i
        SET current_qty = v.current_qty,
            available_qty = v.available_qty,
            reserved_qty = v.reserved_qty
        FROM (VALUES %s) AS v(current_qty, available_qty, reserved_qty, id)
        WHERE i.id = v.id;
    """
    
    execute_values(cur, query, update_data)
    
    print(f"Updated {len(update_data)} rows. Committing...")
    conn.commit()
    cur.close()
    conn.close()
            
    print('Inventory restored successfully from snapshot 1233!')

if __name__ == '__main__':
    restore()
