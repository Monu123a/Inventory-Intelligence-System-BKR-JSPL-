import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.schema import AmazonLiveAllocation, AmazonDLQ, DLQType, AllocationStatus
from app.services.inventory_event_engine import InventoryEventEngine

logger = logging.getLogger(__name__)

class AmazonReconciliationService:
    @staticmethod
    def process_report_item(db: Session, company_id: int, report_item: dict) -> bool:
        """
        Process a single item from an Amazon Settlement/Fulfillment Report.
        Requires strict matching on (order_id, sku, amazon_line_item_id).
        """
        order_id = report_item.get("order_id")
        sku = str(report_item.get("sku", "")).strip().upper()
        line_item_id = report_item.get("amazon_line_item_id")
        shipped_qty = int(report_item.get("shipped_quantity", 0))
        is_return = report_item.get("is_return", False)
        
        try:
            with db.begin_nested():
                # 1. Lock the allocation row
                allocation = db.query(AmazonLiveAllocation).filter(
                    AmazonLiveAllocation.order_id == order_id,
                    AmazonLiveAllocation.sku == sku,
                    AmazonLiveAllocation.amazon_line_item_id == line_item_id,
                    AmazonLiveAllocation.company_id == company_id
                ).with_for_update().first()
                
                if not allocation:
                    # Throw to DLQ
                    dlq = AmazonDLQ(
                        company_id=company_id,
                        dlq_type=DLQType.MATCH_FAILED,
                        reference_id=order_id,
                        error_message="No matching live allocation found for report item",
                        payload=report_item
                    )
                    db.add(dlq)
                    return False
                
                if is_return:
                    # Return Restitution
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=company_id,
                        product_sku=sku,
                        warehouse_id=allocation.warehouse_id,
                        quantity=shipped_qty,
                        event_type="ADD",
                        source="Amazon_Return",
                        reference_id=f"{order_id}_{sku}_{line_item_id}_ADD",
                        metadata_payload={"report_item": report_item}
                    )
                    allocation.status = AllocationStatus.RETURNED
                    allocation.closed = True
                    allocation.allocated_qty = allocation.reconciled_qty
                    allocation.updated_at = datetime.utcnow()
                    return True
                    
                # Forward Reconciliation (Shipment)
                if shipped_qty <= 0:
                    return True # Nothing to deduct
                    
                # Monotonic Math Guard (Never decrease reconciled_qty)
                new_reconciled = max(allocation.reconciled_qty, shipped_qty)
                
                delta_to_deduct = new_reconciled - allocation.reconciled_qty
                
                if delta_to_deduct > 0:
                    # Hard Deduction via Event Engine
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=company_id,
                        product_sku=sku,
                        warehouse_id=allocation.warehouse_id,
                        quantity=delta_to_deduct,
                        event_type="DEDUCT",
                        source="Amazon_Report",
                        reference_id=f"{order_id}_{sku}_{line_item_id}_DEDUCT_{new_reconciled}",
                        metadata_payload={"report_item": report_item}
                    )
                    
                    allocation.reconciled_qty = new_reconciled
                    allocation.updated_at = datetime.utcnow()
                    
                    # If fully reconciled
                    if allocation.reconciled_qty >= allocation.allocated_qty:
                        allocation.closed = True
                        
            return True
        except Exception as e:
            logger.error(f"Failed to reconcile item {sku} for order {order_id}: {e}")
            dlq = AmazonDLQ(
                company_id=company_id,
                dlq_type=DLQType.DATA_MISMATCH,
                reference_id=order_id,
                error_message=str(e),
                payload=report_item
            )
            db.add(dlq)
            return False

