import logging
from datetime import datetime
from typing import Tuple
from sqlalchemy.orm import Session
from dateutil import parser

from app.services.amazon_returns_client import get_amazon_returns_client
from app.models.schema import AmazonReturn

logger = logging.getLogger(__name__)

class AmazonReturnsService:
    @staticmethod
    def sync_returns(db: Session, company_id: int, since: datetime = None) -> Tuple[int, int]:
        """
        Polls Amazon for returns, processes them idempotently, and logs the result.
        Returns a tuple of (records_created, records_updated).
        """
        client = get_amazon_returns_client()
        returns_data = client.fetch_returns(since=since)
        
        records_created = 0
        records_updated = 0
        failed_records = []
        
        for return_data in returns_data:
            amazon_return_id = return_data.get("amazon_return_id")
            order_item_id = return_data.get("order_item_id")
            
            # Idempotency check: Look for existing return by company_id + return_id + item_id
            existing_return = db.query(AmazonReturn).filter(
                AmazonReturn.company_id == company_id,
                AmazonReturn.amazon_return_id == amazon_return_id,
                AmazonReturn.order_item_id == order_item_id
            ).first()
            
            requested_str = return_data.get("requested_at")
            received_str = return_data.get("received_at")
            
            requested_dt = parser.isoparse(requested_str) if requested_str else None
            received_dt = parser.isoparse(received_str) if received_str else None
            
            try:
                with db.begin_nested():
                    if existing_return:
                        # Update status and timestamps if changed
                        updated = False
                        if return_data.get("return_status") != existing_return.return_status:
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
                        # Create new return
                        new_return = AmazonReturn(
                            company_id=company_id,
                            amazon_return_id=amazon_return_id,
                            amazon_order_id=return_data.get("amazon_order_id"),
                            order_item_id=order_item_id,
                            sku=return_data.get("sku"),
                            asin=return_data.get("asin"),
                            product_name=return_data.get("product_name"),
                            quantity=return_data.get("quantity"),
                            return_reason=return_data.get("return_reason"),
                            return_status=return_data.get("return_status"),
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
            
        return records_created, records_updated
