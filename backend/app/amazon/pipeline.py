import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.db import SessionLocal
from app.models.schema import Product, Warehouse, InventoryMovement, AmazonSyncLog, Inventory
from app.services.inventory_event_engine import InventoryEventEngine
from app.amazon.mock_orders import get_mock_shipped_orders

logger = logging.getLogger("amazon.pipeline")

def normalize_sku(raw_sku: str) -> str:
    """
    Business rule for normalizing SKUs from Amazon to internal format.
    - Trim whitespace
    - Uppercase
    """
    return raw_sku.strip().upper()

class AmazonPipeline:
    def __init__(self):
        pass

    def run(self) -> bool:
        """
        Executes the read-only Amazon integration pipeline:
        Fetch Shipped Orders -> Normalize SKUs -> Reduce Inventory -> Log
        """
        logger.info("Starting Amazon SP-API Orders Sync...")
        
        db: Session = SessionLocal()
        
        # Incremental Sync: Get last successful sync time and next_token
        last_sync = db.query(AmazonSyncLog).filter(AmazonSyncLog.status == "SUCCESS").order_by(AmazonSyncLog.sync_start_time.desc()).first()
        
        import os
        from datetime import timedelta
        
        if last_sync and last_sync.sync_start_time:
            last_sync_time = last_sync.sync_start_time
        else:
            # First-run fallback: Use environment variable or default to 24 hours ago
            initial_sync_str = os.getenv("AMAZON_INITIAL_SYNC_START")
            if initial_sync_str:
                last_sync_time = datetime.fromisoformat(initial_sync_str)
            else:
                last_sync_time = datetime.utcnow() - timedelta(days=1)
                
        last_next_token = last_sync.next_token if last_sync else None
        
        sync_log = AmazonSyncLog(
            company_id=1,  # Default company for Amazon sync
            sync_start_time=datetime.utcnow(),
            status="IN_PROGRESS",
            orders_processed=0,
            movements_created=0,
            skipped_duplicates=0,
            failed_items=0,
            unknown_skus="[]",
            api_response_status=None,
            next_token=None,
            errors=None
        )
        db.add(sync_log)
        db.commit()

        try:
            # 1. Fetch Orders (Mocking SP-API for now)
            logger.info(f"Fetching shipped orders from Amazon SP-API since {last_sync_time} (Token: {last_next_token})...")
            # In a real API, we'd pass next_token to the SP-API request
            orders = get_mock_shipped_orders(last_sync_time=last_sync_time)
            sync_log.api_response_status = "200 OK"
            
            # Find a default warehouse to deduct from
            default_warehouse = db.query(Warehouse).filter(Warehouse.status == "Active").first()
            if not default_warehouse:
                raise Exception("No active warehouse found to deduct inventory from.")
            
            # Get the company_id from the warehouse
            company_id = default_warehouse.company_id

            movements_count = 0
            skipped_count = 0
            failed_count = 0
            unknown_skus_list = []
            latest_token = None
            
            for order in orders:
                if order.get("OrderStatus") != "Shipped":
                    continue
                    
                order_id = order["AmazonOrderId"]
                if order.get("NextToken"):
                    latest_token = order.get("NextToken")
                
                for item in order.get("OrderItems", []):
                    raw_sku = item.get("SellerSKU")
                    quantity = item.get("QuantityShipped", 0)
                    order_item_id = item.get("OrderItemId")
                    
                    if not raw_sku or quantity <= 0:
                        continue
                        
                    normalized_sku = normalize_sku(raw_sku)
                    
                    # Idempotency Check: Order ID + OrderItem ID (fallback to SKU)
                    item_identifier = order_item_id if order_item_id else normalized_sku
                    unique_ref = f"{order_id}-{item_identifier}"
                    
                    existing_movement = db.query(InventoryMovement).filter(InventoryMovement.reference_id == unique_ref).first()
                    if existing_movement:
                        logger.info(f"Duplicate found for {unique_ref}. Skipping.")
                        skipped_count += 1
                        continue
                    
                    # Verify product exists for this company
                    product = db.query(Product).filter(
                        Product.sku == normalized_sku,
                        Product.company_id == company_id
                    ).first()
                    if not product:
                        logger.warning(f"Order {order_id} has unknown SKU: {normalized_sku}. Recording failure.")
                        failed_count += 1
                        if normalized_sku not in unknown_skus_list:
                            unknown_skus_list.append(normalized_sku)
                        continue
                        
                    # Use InventoryEventEngine for proper stock deduction and movement tracking
                    try:
                        InventoryEventEngine.process_event(
                            db=db,
                            company_id=company_id,
                            product_sku=normalized_sku,
                            warehouse_id=default_warehouse.id,
                            quantity=quantity,
                            event_type="DEDUCT",
                            source="AMAZON_SYNC",
                            reference_id=unique_ref,
                            metadata_payload={"order_id": order_id, "order_item_id": order_item_id}
                        )
                    except Exception as item_err:
                        logger.error(f"Failed to process item {unique_ref}: {item_err}")
                        failed_count += 1
                        continue
                        
                    movements_count += 1

            sync_log.orders_processed = len(orders)
            sync_log.movements_created = movements_count
            sync_log.skipped_duplicates = skipped_count
            sync_log.failed_items = failed_count
            
            import json
            sync_log.unknown_skus = json.dumps(unknown_skus_list)
            sync_log.next_token = latest_token
            
            sync_log.status = "SUCCESS"
            sync_log.sync_end_time = datetime.utcnow()
            db.commit()
            
            logger.info(f"Amazon Sync Complete. Processed {len(orders)} orders, created {movements_count} movements, skipped {skipped_count}, failed {failed_count}.")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Amazon Sync Failed: {e}")
            sync_log.status = "FAILED"
            sync_log.api_response_status = "500 ERROR"
            sync_log.errors = str(e)
            sync_log.sync_end_time = datetime.utcnow()
            db.commit()
            return False
        finally:
            db.close()
