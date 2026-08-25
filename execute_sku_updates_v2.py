import json
import psycopg2

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

with open('/Users/harshahlawat/.gemini/antigravity/brain/d247ab24-ed3f-44f6-936a-9d5c40d0c0be/sku_analysis.json', 'r') as f:
    data = json.load(f)

print(f"Executing Phase 1: Direct Rename for {len(data['new_vs_old'])} products.")
rename_count = 0
for item in data['new_vs_old']:
    cname = item['company']
    old_sku = item['old_sku']
    new_sku = item['new_sku']
    
    cur.execute("SELECT id FROM companies WHERE name = %s", (cname,))
    cid = cur.fetchone()[0]
    
    cur.execute("UPDATE products SET sku = %s WHERE sku = %s AND company_id = %s", (new_sku, old_sku, cid))
    rename_count += cur.rowcount

conn.commit()
print(f"Successfully renamed and committed {rename_count} products.")

print(f"\nExecuting Phase 2: Stock Merge for {len(data['requires_merge'])} products.")
merge_count = 0
for item in data['requires_merge']:
    cname = item['company']
    old_sku = item['old_sku']
    new_sku = item['new_sku']
    
    cur.execute("SELECT id FROM companies WHERE name = %s", (cname,))
    cid = cur.fetchone()[0]
    
    # Find Source (The wrong one)
    cur.execute("SELECT id FROM products WHERE sku = %s AND company_id = %s", (old_sku, cid))
    source_res = cur.fetchone()
    if not source_res:
        continue
    source_id = source_res[0]
    
    # Find Target (The correct one that already exists)
    cur.execute("SELECT id FROM products WHERE sku = %s AND company_id = %s", (new_sku, cid))
    target_res = cur.fetchone()
    if not target_res:
        continue
    target_id = target_res[0]
    
    # Move Inventory
    cur.execute("SELECT id, warehouse_id, current_qty, reserved_qty, available_qty FROM inventory WHERE product_id = %s", (source_id,))
    source_invs = cur.fetchall()
    
    for inv_id, w_id, c_qty, r_qty, a_qty in source_invs:
        # Check if target has inventory in this warehouse
        cur.execute("SELECT id FROM inventory WHERE product_id = %s AND warehouse_id = %s", (target_id, w_id))
        target_inv = cur.fetchone()
        
        if target_inv:
            # Add quantities
            cur.execute("""
                UPDATE inventory 
                SET current_qty = current_qty + %s,
                    reserved_qty = reserved_qty + %s,
                    available_qty = available_qty + %s
                WHERE id = %s
            """, (c_qty, r_qty, a_qty, target_inv[0]))
            # Delete source inventory row
            cur.execute("DELETE FROM inventory WHERE id = %s", (inv_id,))
        else:
            # Redirect the source inventory row to the target product
            cur.execute("UPDATE inventory SET product_id = %s WHERE id = %s", (target_id, inv_id))
            
    # Mark source product as inactive and rename SKU to avoid collision
    merged_sku = f"{old_sku}-MERGED-{source_id}"
    cur.execute("UPDATE products SET sku = %s, status = 'Inactive' WHERE id = %s", (merged_sku, source_id))
    
    conn.commit() # Commit after each successful merge
    merge_count += 1

print(f"Successfully merged and committed {merge_count} products.")

cur.close()
conn.close()
