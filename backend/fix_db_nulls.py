import sqlite3
import datetime

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

# Fix inventory nulls
cursor.execute("UPDATE inventory SET reserved_qty = 0 WHERE reserved_qty IS NULL")
cursor.execute("UPDATE inventory SET available_qty = current_qty WHERE available_qty IS NULL")
cursor.execute("UPDATE inventory SET last_updated = ? WHERE last_updated IS NULL", (datetime.datetime.utcnow().isoformat(),))

# Fix warehouse code nulls
cursor.execute("UPDATE warehouses SET code = 'WH-' || id WHERE code IS NULL")

conn.commit()
conn.close()
print("Fixed NULL values in database")
