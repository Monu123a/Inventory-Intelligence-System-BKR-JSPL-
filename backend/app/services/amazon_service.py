import logging
import json
from datetime import datetime, timedelta
from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.amazon_client import get_amazon_client
from app.models.schema import Product, WarehouseExternalMapping
from app.models.schema import AmazonLiveAllocation, AmazonOrderEventLog, AmazonDLQ, AmazonNetworkType, AllocationStatus, DLQType

logger = logging.getLogger(__name__)

class AmazonService:
    @staticmethod
    def poll_orders(db: Session, company_id: int, since=None) -> Tuple[int, int]:
        """
        Polls Amazon for orders, creates soft allocations (upsert), and handles the lifecycle.
        Returns a tuple of (processed_count, skipped_count).
        """
        client = get_amazon_client()
        
        # 15 min + 5 min buffer = 20 mins back
        since = since or (datetime.utcnow() - timedelta(minutes=20))
        
        try:
            orders = client.fetch_orders(since=since)
        except Exception as e:
            logger.error(f"Failed to fetch from SP-API: {e}")
            dlq = AmazonDLQ(
                company_id=company_id,
                dlq_type=DLQType.API_FAILURE,
                error_message=str(e),
                payload={"since": since.isoformat()}
            )
            db.add(dlq)
            db.commit()
            return 0, 0
            
        processed_count = 0
        skipped_count = 0
        
        for order in orders:
            order_id = order.get("order_id")
            amazon_status = order.get("status")
            channel = order.get("fulfillment_channel", "MFN")
            last_update_str = order.get("last_update_date")
            last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00")).replace(tzinfo=None) if last_update_str else datetime.utcnow()
            
            # Map Amazon status to our AllocationStatus
            status_map = {
                "Pending": AllocationStatus.PENDING,
                "Unshipped": AllocationStatus.UNSHIPPED,
                "PartiallyShipped": AllocationStatus.UNSHIPPED, # Treat as unshipped until report
                "Shipped": AllocationStatus.SHIPPED,
                "Canceled": AllocationStatus.CANCELLED,
            }
            mapped_status = status_map.get(amazon_status, AllocationStatus.PENDING)
            
            # Identify target network
            network = AmazonNetworkType.MFN if channel == "MFN" else AmazonNetworkType.AFN
            
            # Find a warehouse mapping to associate (optional for soft allocation, but good for UI)
            mapping = db.query(WarehouseExternalMapping).filter(WarehouseExternalMapping.amazon_network == network).first()
            warehouse_id = mapping.warehouse_id if mapping else None
            
            for item in order.get("items", []):
                sku = str(item.get("sku", "")).strip().upper()
                line_item_id = item.get("amazon_line_item_id", "default")
                qty = int(item.get("quantity") or 0)
                
                if not sku:
                    continue
                    
                # Verify SKU exists
                prod_exists = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
                if not prod_exists:
                    # Throw to DLQ
                    dlq = AmazonDLQ(
                        company_id=company_id,
                        dlq_type=DLQType.DATA_MISMATCH,
                        reference_id=order_id,
                        error_message=f"Unknown SKU: {sku}",
                        payload={"item": item}
                    )
                    db.add(dlq)
                    skipped_count += 1
                    continue
                
                try:
                    with db.begin_nested():
                        # UPSERT Logic (Optimistic Versioning)
                        existing = db.query(AmazonLiveAllocation).filter(
                            AmazonLiveAllocation.order_id == order_id,
                            AmazonLiveAllocation.sku == sku,
                            AmazonLiveAllocation.amazon_line_item_id == line_item_id
                        ).with_for_update().first() # Row-level lock
                        
                        if existing:
                            # Version check
                            if existing.updated_at >= last_update:
                                skipped_count += 1
                                continue
                            
                            # Status Guard: If it was cancelled/refunded, don't reopen it
                            if existing.status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]:
                                skipped_count += 1
                                continue
                                
                            prev_status = existing.status
                            existing.status = mapped_status
                            existing.allocated_qty = qty
                            existing.updated_at = last_update
                            
                            if mapped_status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]:
                                existing.closed = True
                                existing.allocated_qty = existing.reconciled_qty # Instantly restore soft allocation
                                
                            if prev_status != mapped_status:
                                event = AmazonOrderEventLog(
                                    allocation_id=existing.id,
                                    previous_status=prev_status.value,
                                    new_status=mapped_status.value,
                                    timestamp=datetime.utcnow()
                                )
                                db.add(event)
                                
                        else:
                            # Create new allocation
                            closed = mapped_status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]
                            final_qty = 0 if closed else qty
                            
                            allocation = AmazonLiveAllocation(
                                company_id=company_id,
                                order_id=order_id,
                                sku=sku,
                                amazon_line_item_id=line_item_id,
                                warehouse_id=warehouse_id,
                                amazon_network_at_allocation=network,
                                allocated_qty=final_qty,
                                status=mapped_status,
                                closed=closed,
                                updated_at=last_update
                            )
                            db.add(allocation)
                            db.flush() # get ID
                            
                            event = AmazonOrderEventLog(
                                allocation_id=allocation.id,
                                previous_status=None,
                                new_status=mapped_status.value,
                                timestamp=datetime.utcnow()
                            )
                            db.add(event)
                            
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process item {sku} for order {order_id}: {e}")
                    # Savepoint rolled back
                    skipped_count += 1
                    
        db.commit()
        return processed_count, skipped_count

