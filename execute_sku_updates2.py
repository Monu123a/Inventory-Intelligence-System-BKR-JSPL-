import psycopg2
import re
import csv
import os

DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id, company_id, sku FROM products WHERE sku IS NOT NULL")
existing_skus = {}
for pid, cid, sku in cur.fetchall():
    sku_upper = str(sku).strip().upper()
    if cid not in existing_skus:
        existing_skus[cid] = {}
    existing_skus[cid][sku_upper] = pid

query = """
    SELECT p.id, c.name, p.company_id, p.sku, p.name 
    FROM products p 
    JOIN companies c ON p.company_id = c.id
    WHERE p.hsn IS NULL OR p.hsn = ''
"""
cur.execute(query)
missing_hsn_products = cur.fetchall()

pattern = re.compile(r'\b[A-Za-z]{2}\d{4,}\b')

list_updated = []
list_no_pattern = []
list_merge = []

tables_to_update = [
    "inventory_movements",
    "inventory_snapshots",
    "sale_items",
    "replenishment_recommendations",
    "stock_transfer_items",
    "defective_inventory",
    "sales_return_items",
    "delivery_challan_items",
    "service_parts",
    "damage_claims",
    "fc_dispatch_items",
    "fc_return_items"
]

def merge_inventory(old_id, new_id):
    cur.execute("SELECT id, warehouse_id, current_qty, reserved_qty, available_qty FROM inventory WHERE product_id = %s", (old_id,))
    for row in cur.fetchall():
        inv_id, w_id, c_qty, r_qty, a_qty = row
        cur.execute("SELECT id FROM inventory WHERE product_id = %s AND warehouse_id = %s", (new_id, w_id))
        target_inv = cur.fetchone()
        if target_inv:
            cur.execute("""
                UPDATE inventory 
                SET current_qty = current_qty + %s, 
                    reserved_qty = reserved_qty + %s, 
                    available_qty = available_qty + %s 
                WHERE id = %s
            """, (c_qty, r_qty, a_qty, target_inv[0]))
            cur.execute("DELETE FROM inventory WHERE id = %s", (inv_id,))
        else:
            cur.execute("UPDATE inventory SET product_id = %s WHERE id = %s", (new_id, inv_id))

def handle_service_reminders(old_id, new_id):
    cur.execute("SELECT id, sale_id FROM service_reminders WHERE product_id = %s", (old_id,))
    for row in cur.fetchall():
        rem_id, sale_id = row
        cur.execute("SELECT id FROM service_reminders WHERE product_id = %s AND sale_id = %s", (new_id, sale_id))
        if cur.fetchone():
            cur.execute("DELETE FROM service_reminders WHERE id = %s", (rem_id,))
        else:
            cur.execute("UPDATE service_reminders SET product_id = %s WHERE id = %s", (new_id, rem_id))

for row in missing_hsn_products:
    old_id, comp_name, cid, old_sku, name = row
    old_sku_upper = str(old_sku).strip().upper()
    
    found = pattern.search(name)
    if not found:
        list_no_pattern.append((comp_name, old_sku, name))
        continue
        
    raw_match = found.group(0).upper()
    new_sku = raw_match[:6]
    
    if new_sku == old_sku_upper:
        list_updated.append((comp_name, old_sku, new_sku, name, "Unchanged"))
        continue
        
    if new_sku in existing_skus.get(cid, {}):
        target_id = existing_skus[cid][new_sku]
        if target_id == old_id:
            continue
            
        list_merge.append((comp_name, old_sku, new_sku, name))
        
        # Merge operation
        merge_inventory(old_id, target_id)
        handle_service_reminders(old_id, target_id)
        for table in tables_to_update:
            try:
                cur.execute(f"UPDATE {table} SET product_id = %s WHERE product_id = %s", (target_id, old_id))
            except Exception as e:
                pass # Just ignore if table/col doesn't exist in this specific DB state
                
        # Also handle replacement_product_id if it exists
        try:
            cur.execute("UPDATE sales_return_items SET replacement_product_id = %s WHERE replacement_product_id = %s", (target_id, old_id))
        except Exception:
            pass
        
        # Delete old product
        cur.execute("DELETE FROM products WHERE id = %s", (old_id,))
    else:
        list_updated.append((comp_name, old_sku, new_sku, name, "Updated"))
        cur.execute("UPDATE products SET sku = %s WHERE id = %s", (new_sku, old_id))
        existing_skus[cid][new_sku] = old_id

conn.commit()

out_dir = "/Users/harshahlawat/.gemini/antigravity/brain/d247ab24-ed3f-44f6-936a-9d5c40d0c0be"
import json
with open(os.path.join(out_dir, "updated_skus.json"), "w") as f:
    json.dump([{"Company": c, "Old SKU": o, "New SKU": n, "Name": m, "Status": s} for c,o,n,m,s in list_updated], f, indent=2)

with open(os.path.join(out_dir, "merge_skus.json"), "w") as f:
    json.dump([{"Company": c, "Old Bad SKU": o, "Target SKU": n, "Name": m} for c,o,n,m in list_merge], f, indent=2)

with open(os.path.join(out_dir, "no_pattern_skus.json"), "w") as f:
    json.dump([{"Company": c, "SKU": o, "Name": m} for c,o,m in list_no_pattern], f, indent=2)

print(f"Updated (Safe): {len(list_updated)}")
print(f"Merge required (Clash): {len(list_merge)}")
print(f"No Pattern Found: {len(list_no_pattern)}")

cur.close()
conn.close()
