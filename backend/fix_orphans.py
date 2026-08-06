import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')
print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT id, name FROM warehouses WHERE hub_id IS NULL")
orphans = c.fetchall()

if orphans:
    print(f"Found {len(orphans)} orphan warehouses.")
    for wh_id, name in orphans:
        if not name.endswith("[MIGRATION REQUIRED - ASSIGN HUB]"):
            new_name = f"{name} [MIGRATION REQUIRED - ASSIGN HUB]"
            c.execute("UPDATE warehouses SET name = ? WHERE id = ?", (new_name, wh_id))
            print(f"Updated Warehouse {wh_id}: {new_name}")
    conn.commit()
else:
    print("No orphan warehouses found.")

# Update code for warehouses where code is null
c.execute("SELECT id, name FROM warehouses WHERE code IS NULL OR code = ''")
empty_codes = c.fetchall()

if empty_codes:
    print(f"Found {len(empty_codes)} warehouses with empty code.")
    for wh_id, name in empty_codes:
        new_code = f"MIG-{wh_id}"
        c.execute("UPDATE warehouses SET code = ? WHERE id = ?", (new_code, wh_id))
        print(f"Assigned code {new_code} to Warehouse {wh_id}")
    conn.commit()
else:
    print("No warehouses with empty code found.")

conn.close()
print("Data migration complete.")
