import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem

db = SessionLocal()
req = FCDispatchBatchRequest(
    source_warehouse_id=39,
    warehouse_ids=[14],
    items=[FCDispatchRequestItem(product_id=1, quantity=1)]
)
try:
    FCDispatchService.create_batch_dispatch(db, 2, req, 1)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
