import sys
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR, stream=sys.stdout)

env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

sys.path.append(os.path.join(os.getcwd(), 'backend'))
import app.models.db as db_module
from app.models.db import SessionLocal
from app.services.amazon_reconciliation_service import AmazonReconciliationService

db = SessionLocal()
AmazonReconciliationService.process_report_item(db, 2, {
    "order_id": "AMZ-123",
    "sku": "TSTAMZ01",
    "amazon_line_item_id": "LINE-1",
    "shipped_quantity": 6,
    "is_return": False
})
