from sqlalchemy import create_engine, text
DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    print("sale_items with empty HSN:")
    res = conn.execute(text("SELECT id, sku, hsn_sac, created_at FROM sale_items WHERE sku = 'HM0038'"))
    for row in res: print(row)
    
    print("fc_dispatch_items with empty HSN:")
    res = conn.execute(text("SELECT id, sku_snapshot, hsn_snapshot FROM fc_dispatch_items WHERE sku_snapshot = 'HM0038'"))
    for row in res: print(row)
    
    print("delivery_challan_items with empty HSN:")
    res = conn.execute(text("SELECT id, sku_snapshot, hsn_snapshot FROM delivery_challan_items WHERE sku_snapshot = 'HM0038'"))
    for row in res: print(row)
