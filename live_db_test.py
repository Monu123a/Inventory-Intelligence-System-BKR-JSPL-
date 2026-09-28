import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.models.schema import User, Warehouse, Company

LIVE_DB_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
engine = create_engine(LIVE_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

# Find a valid product in JSPL Central (or BKR)
req = FCDispatchBatchRequest(
    source_warehouse_id=39, # BKR Central (assuming it's 39, let's find it dynamically)
    warehouse_ids=[14], # JSPL Central
    dispatch_type="STANDARD",
    items=[FCDispatchRequestItem(product_id=5993, quantity=1)]
)

bkr = db.query(Company).filter_by(code='BKR').first()
bkr_wh = db.query(Warehouse).filter_by(company_id=bkr.id, warehouse_type='CENTRAL').first()
jspl = db.query(Company).filter_by(code='JSPL').first()
jspl_wh = db.query(Warehouse).filter_by(company_id=jspl.id, warehouse_type='CENTRAL').first()
user = db.query(User).filter_by(username='test_admin').first() or db.query(User).first()

req.source_warehouse_id = bkr_wh.id
req.warehouse_ids = [jspl_wh.id]
req.items[0].product_id = db.query(Warehouse).first().id # just put a dummy ID or fetch a real product

try:
    print("Testing create_batch_dispatch against LIVE DB...")
    # Just to get the crash trace, we will wrap in try-except
    FCDispatchService.create_batch_dispatch(db, bkr.id, req, user.id)
    print("Success?!")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.rollback()
    print("Rolled back to not break live data.")
