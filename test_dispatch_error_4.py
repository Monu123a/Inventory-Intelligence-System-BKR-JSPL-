import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.models.schema import Warehouse, WarehouseType

db = SessionLocal()
w3 = db.query(Warehouse).filter_by(id=3).first()
orig_type = w3.warehouse_type
w3.warehouse_type = WarehouseType.CENTRAL
db.commit()

req = FCDispatchBatchRequest(
    source_warehouse_id=3,
    warehouse_ids=[14], # JSPL Central
    items=[FCDispatchRequestItem(product_id=1155, quantity=1)]
)
try:
    FCDispatchService.create_batch_dispatch(db, 2, req, 1) # BKR -> JSPL
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    w3.warehouse_type = orig_type
    db.commit()
