import sys
import os
import json
sys.path.append(os.path.abspath('backend'))
from sqlalchemy import create_engine, update, bindparam, text
from app.models.schema import Inventory

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
engine = create_engine(RENDER_POSTGRES_URL, connect_args={"options": "-c statement_timeout=30000"})

def restore():
    print('Restoring inventory quantities from snapshot 1233...')
    with open('scratch/snapshot_1233.json', 'r') as f:
        snapshot = json.load(f)
    
    update_data = []
    for data in snapshot['inventory']:
        update_data.append({
            'b_id': data['id'],
            'current_qty': data['current_qty'],
            'available_qty': data['available_qty'],
            'reserved_qty': data['reserved_qty']
        })
        
    stmt = (
        update(Inventory)
        .where(Inventory.id == bindparam('b_id'))
        .values(
            current_qty=bindparam('current_qty'),
            available_qty=bindparam('available_qty'),
            reserved_qty=bindparam('reserved_qty')
        )
    )
    
    with engine.begin() as conn:
        conn.execute(stmt, update_data)
            
    print('Inventory restored successfully from snapshot 1233!')

if __name__ == '__main__':
    restore()
