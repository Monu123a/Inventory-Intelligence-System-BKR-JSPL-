import logging
import json
from datetime import datetime
from typing import Tuple
from sqlalchemy.orm import Session

from app.services.amazon_client import get_amazon_client
from app.services.inventory_event_engine import InventoryEventEngine
from app.models.schema import AmazonSyncLog, Product
from app.models.schema import WarehouseExternalMapping

logger = logging.getLogger(__name__)

class AmazonService:
    @staticmethod
    def poll_orders(db: Session, company_id: int, since: datetime = None) -> Tuple[int, int]:
        """
        Polls Amazon for orders, processes them idempotently, and logs the result.
        Returns a tuple of (processed_count, skipped_count).
        """
        client = get_amazon_client()
        orders = client.fetch_orders(since=since)
        
        processed_count = 0
        skipped_count = 0
        
        # We no longer use a default warehouse. FC code must be mapped.
            
        for order in orders:
            order_id = order.get("order_id")
            
            # Duplicate check
            existing_log = db.query(AmazonSyncLog).filter(AmazonSyncLog.order_id == order_id, AmazonSyncLog.company_id == company_id).first()
            if existing_log:
                skipped_count += 1
                continue
                
            # Use savepoint so we can rollback a single order without affecting others or caller
            try:
                with db.begin_nested():
                    items = order.get("items", [])
                    fc_code = order.get("fulfillment_center")
                    
                    if not fc_code:
                        raise ValueError("No fulfillment center in order")
                        
                    # Lookup External Mapping
                    mapping = db.query(WarehouseExternalMapping).filter(
                        WarehouseExternalMapping.marketplace == "Amazon",
                        WarehouseExternalMapping.external_code == fc_code
                    ).first()
                    
                    if not mapping:
                        # Log to quarantine
                        sync_log = AmazonSyncLog(
                            company_id=company_id, 
                            order_id=order_id, 
                            status="Quarantined", 
                            errors="Needs Mapping",
                            unknown_skus=f'["{fc_code}"]' # Hack to store FC code for UI for now
                        )
                        db.add(sync_log)
                        skipped_count += 1
                        continue
                        
                    warehouse_id = mapping.warehouse_id
                    
                    # Pre-flight check: verify all SKUs exist
                    missing_skus = []
                    for item in items:
                        sku_val = str(item.get("sku", "")).strip().upper()[:6]
                        if not sku_val:
                            continue
                        prod_exists = db.query(Product).filter(Product.sku == sku_val, Product.company_id == company_id).first()
                        if not prod_exists:
                            missing_skus.append(sku_val)
                            
                    if missing_skus:
                        sync_log = AmazonSyncLog(
                            company_id=company_id, 
                            order_id=order_id, 
                            status="Quarantined", 
                            errors="Unknown SKUs",
                            unknown_skus=json.dumps(list(set(missing_skus)))
                        )
                        db.add(sync_log)
                        skipped_count += 1
                        continue
                    
                    # Process each item in the order
                    for idx, item in enumerate(items):
                        sku = str(item.get("sku", "")).strip()[:6]
                        quantity = int(item.get("quantity") or 0)
                        
                        movement = InventoryEventEngine.process_event(
                            db=db,
                            company_id=company_id,
                            product_sku=sku,
                            warehouse_id=warehouse_id,
                            quantity=quantity,
                            event_type="DEDUCT",
                            source="Amazon",
                            reference_id=order_id,
                            metadata_payload={"amazon_order": order, "line_id": str(idx)}
                        )
                        
                    # Add AmazonSyncLog ONLY after successful processing
                    sync_log = AmazonSyncLog(company_id=company_id, order_id=order_id, status="Processed")
                    db.add(sync_log)
                    
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process order {order_id}: {e}")
                # Savepoint rolls back automatically
                
        return processed_count, skipped_count
