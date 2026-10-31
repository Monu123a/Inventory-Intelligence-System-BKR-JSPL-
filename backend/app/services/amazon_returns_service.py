import logging
from datetime import datetime
from typing import Tuple
from sqlalchemy.orm import Session
from dateutil import parser

from app.services.amazon_returns_client import get_amazon_returns_client
from app.models.schema import AmazonReturn

logger = logging.getLogger(__name__)

def safe_parse_dt(dt_str) -> datetime:
    if not dt_str:
        return None
    try:
        from datetime import timezone
        dt = parser.parse(str(dt_str))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        try:
            return parser.isoparse(str(dt_str)).replace(tzinfo=None)
        except Exception:
            return None

class AmazonReturnsService:
    @staticmethod
    def sync_returns(db: Session, company_id: int, since: datetime = None) -> Tuple[int, int]:
        """
        Polls Amazon for returns, processes them idempotently, and logs the result.
        Returns a tuple of (records_created, records_updated).
        NOTE: Returns synced from Amazon do NOT revert inventory automatically.
        They are stored with inspection_status=None and require explicit human verification
        before any inventory movements occur.
        """
        client = get_amazon_returns_client()
        returns_data = client.fetch_returns(since=since)
        
        records_created = 0
        records_updated = 0
        failed_records = []
        
        for return_data in returns_data:
            amazon_return_id = return_data.get("amazon_return_id")
            order_item_id = return_data.get("order_item_id")
            if not amazon_return_id or not order_item_id:
                continue
            
            # Idempotency check: Look for existing return by company_id + return_id + item_id
            existing_return = db.query(AmazonReturn).filter(
                AmazonReturn.company_id == company_id,
                AmazonReturn.amazon_return_id == amazon_return_id,
                AmazonReturn.order_item_id == order_item_id
            ).first()
            
            requested_str = return_data.get("requested_at")
            received_str = return_data.get("received_at")
            
            requested_dt = safe_parse_dt(requested_str)
            received_dt = safe_parse_dt(received_str)
            
            try:
                with db.begin_nested():
                    if existing_return:
                        # Update status and timestamps if changed
                        updated = False
                        if return_data.get("return_status") and return_data.get("return_status") != existing_return.return_status:
                            existing_return.return_status = return_data.get("return_status")
                            updated = True
                        if received_dt and existing_return.received_at != received_dt:
                            existing_return.received_at = received_dt
                            updated = True
                            
                        if updated:
                            existing_return.last_synced_at = datetime.utcnow()
                            db.flush()
                            records_updated += 1
                    else:
                        # Create new unverified return (inspection_status=None)
                        new_return = AmazonReturn(
                            company_id=company_id,
                            amazon_return_id=amazon_return_id,
                            amazon_order_id=return_data.get("amazon_order_id"),
                            order_item_id=order_item_id,
                            sku=return_data.get("sku"),
                            asin=return_data.get("asin"),
                            product_name=return_data.get("product_name"),
                            quantity=return_data.get("quantity") or 1,
                            return_reason=return_data.get("return_reason"),
                            return_status=return_data.get("return_status") or "Received",
                            inspection_status=None,  # Must be explicitly verified before restock
                            requested_at=requested_dt,
                            received_at=received_dt,
                            last_synced_at=datetime.utcnow()
                        )
                        db.add(new_return)
                        db.flush()
                        records_created += 1
            except Exception as e:
                # db.rollback() happens automatically because of begin_nested() context manager
                logger.error(
                    f"Amazon return failed for record_id={amazon_return_id}",
                    exc_info=True
                )
                failed_records.append({
                    "record_id": amazon_return_id,
                    "error": str(e)
                })
                continue

        if failed_records:
            raise Exception(f"PartialBatchFailureException: {failed_records}")

        # Also synchronize MFN and FC returns from amazon_live_allocations
        try:
            alloc_created, alloc_updated = AmazonReturnsService.sync_returns_from_allocations(db, company_id=company_id)
            records_created += alloc_created
            records_updated += alloc_updated
        except Exception as alloc_err:
            logger.error(f"Error syncing returns from allocations: {alloc_err}", exc_info=True)
            
        return records_created, records_updated

    @staticmethod
    def sync_returns_from_allocations(db: Session, company_id: int) -> Tuple[int, int]:
        """
        Synchronizes all return / refund records from amazon_live_allocations (both MFN and FC)
        into amazon_returns table so warehouse staff can verify, inspect, and restock them.
        """
        from app.models.schema import AmazonLiveAllocation, AllocationStatus, AmazonNetworkType, Product
        from sqlalchemy import or_

        alloc_returns = (
            db.query(AmazonLiveAllocation)
            .filter(
                AmazonLiveAllocation.company_id == company_id,
                AmazonLiveAllocation.status == AllocationStatus.RETURNED
            )
            .all()
        )

        created = 0
        updated = 0

        for a in alloc_returns:
            is_mfn = (
                a.amazon_network_at_allocation == AmazonNetworkType.MFN or
                a.warehouse_id == 38 or
                (a.invoice_number and a.invoice_number.upper().startswith("IN-"))
            )
            channel = "MFN" if is_mfn else "AFN"
            ret_id = f"{channel}-{a.invoice_number or a.order_id}"
            item_id = a.amazon_line_item_id or f"{a.order_id}-{a.sku}"

            existing = db.query(AmazonReturn).filter(
                AmazonReturn.company_id == company_id,
                AmazonReturn.amazon_return_id == ret_id,
                AmazonReturn.order_item_id == item_id
            ).first()

            prod = db.query(Product).filter(
                Product.sku == a.sku,
                Product.company_id == company_id
            ).first()

            if existing:
                pass
            else:
                new_ret = AmazonReturn(
                    company_id=company_id,
                    amazon_return_id=ret_id,
                    amazon_order_id=a.order_id,
                    order_item_id=item_id,
                    sku=a.sku,
                    asin=None,
                    product_name=prod.name if prod else a.sku,
                    quantity=abs(a.allocated_qty or 1),
                    return_reason=f"{channel} Customer Return ({a.invoice_number or 'Standard'})",
                    return_status="Received",
                    inspection_status=None,
                    requested_at=a.order_date or a.shipment_date,
                    received_at=a.shipment_date or a.order_date,
                    last_synced_at=datetime.utcnow()
                )
                db.add(new_ret)
                created += 1

        if created > 0:
            db.commit()

        return created, updated
