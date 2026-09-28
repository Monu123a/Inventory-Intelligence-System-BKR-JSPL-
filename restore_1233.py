import sys
import os
import json
sys.path.append(os.path.abspath('backend'))
from sqlalchemy import create_engine, update, bindparam, text
from app.models.schema import Inventory

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
engine = create_engine(RENDER_POSTGRES_URL)

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
        
        # Now restore inventory_movements if they want
        if 'inventory_movements' in snapshot and len(snapshot['inventory_movements']) > 0:
            print("Truncating and restoring inventory_movements...")
            conn.execute(text("TRUNCATE TABLE inventory_movements RESTART IDENTITY CASCADE"))
            
            insert_stmt = text("""
                INSERT INTO inventory_movements 
                (id, company_id, timestamp, product_id, warehouse_id, qty_before, qty_changed, qty_after, source, reference_id, operation_id, user_id, metadata_payload)
                VALUES (:id, :company_id, :timestamp, :product_id, :warehouse_id, :qty_before, :qty_changed, :qty_after, :source, :reference_id, :operation_id, :user_id, :metadata_payload)
            """)
            
            for m in snapshot['inventory_movements']:
                conn.execute(insert_stmt, {
                    'id': m['id'],
                    'company_id': m['company_id'],
                    'timestamp': m['timestamp'],
                    'product_id': m['product_id'],
                    'warehouse_id': m['warehouse_id'],
                    'qty_before': m['qty_before'],
                    'qty_changed': m['qty_changed'],
                    'qty_after': m['qty_after'],
                    'source': m['source'],
                    'reference_id': m['reference_id'],
                    'operation_id': m['operation_id'],
                    'user_id': m['user_id'],
                    'metadata_payload': json.dumps(m['metadata_payload']) if m['metadata_payload'] else None
                })
            
    print('Inventory and movements restored successfully from snapshot 1233!')

if __name__ == '__main__':
    restore()
