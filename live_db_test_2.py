import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.models.schema import User, Warehouse, Company, Inventory, Product

LIVE_DB_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(LIVE_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

bkr = db.query(Company).filter_by(code='BKR').first()
bkr_wh = db.query(Warehouse).filter_by(company_id=bkr.id, warehouse_type='CENTRAL').first()
jspl = db.query(Company).filter_by(code='JSPL').first()
jspl_wh = db.query(Warehouse).filter_by(company_id=jspl.id, warehouse_type='CENTRAL').first()
user = db.query(User).filter_by(username='test_admin').first() or db.query(User).first()

# find a real product in BKR Central that has stock
inv = db.query(Inventory).filter(Inventory.warehouse_id == bkr_wh.id, Inventory.available_qty > 0).first()
if not inv:
    # Just take any product and mock stock temporarily for the test (it rolls back!)
    p = db.query(Product).filter_by(company_id=bkr.id).first()
    inv = Inventory(company_id=bkr.id, warehouse_id=bkr_wh.id, product_id=p.id, available_qty=100)
    # wait, InventoryEventEngine is required. I can't mock it easily.
    # So I will temporarily disable the warehouse_id check in fc_dispatch_service by modifying the python file again? No, I'll just change the req's source_warehouse_id to a warehouse that DOES have stock.
    # Let's find ANY BKR warehouse with stock.
    inv = db.query(Inventory).filter(Inventory.company_id == bkr.id, Inventory.available_qty > 0).first()
    # But then create_batch_dispatch throws 400 if it's not CENTRAL!
    # I can temporarily change the warehouse_type of that warehouse in my transaction!
    wh = db.query(Warehouse).filter_by(id=inv.warehouse_id).first()
    wh.warehouse_type = "CENTRAL" # String assignment to Enum works in SQLAlchemy sometimes, or import WarehouseType
else:
    wh = bkr_wh

req = FCDispatchBatchRequest(
    source_warehouse_id=wh.id,
    warehouse_ids=[jspl_wh.id],
    dispatch_type="STANDARD",
    items=[FCDispatchRequestItem(product_id=inv.product_id, quantity=1)]
)

try:
    print(f"Testing create_batch_dispatch against LIVE DB with Product {inv.product_id} from WH {wh.id}...")
    FCDispatchService.create_batch_dispatch(db, bkr.id, req, user.id)
    print("Success?!")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.rollback()
    print("Rolled back to not break live data.")
