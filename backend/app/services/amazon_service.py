import logging
import json
import time
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.amazon_client import get_amazon_client
from app.models.schema import (
    Product, Warehouse, WarehouseExternalMapping, AmazonSyncLog,
    AmazonLiveAllocation, AmazonOrderEventLog, AmazonDLQ, AmazonNetworkType, AllocationStatus, DLQType
)

logger = logging.getLogger(__name__)

class AmazonService:
    @staticmethod
    def sync_orders(
        db: Session, 
        company_id: int, 
        since: datetime = None, 
        force_backfill: bool = False,
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        Enterprise Amazon Order Synchronizer:
        - Auto-watermarks based on last successful sync or initial backfill date.
        - Streams pages with NextToken pagination.
        - Incremental page-level commits so data is never lost.
        - Skips expensive line item lookups for already-synced orders.
        - Records status in AmazonSyncLog.
        """
        start_time = datetime.utcnow()
        client = get_amazon_client()

        # 1. Determine sync start date
        if since is None:
            if force_backfill:
                since = datetime(2026, 8, 1)
            else:
                last_log = db.query(AmazonSyncLog).filter(
                    AmazonSyncLog.company_id == company_id,
                    AmazonSyncLog.status == "SUCCESS"
                ).order_by(AmazonSyncLog.id.desc()).first()

                watermark = None
                if last_log and last_log.api_response_status and last_log.api_response_status.startswith("watermark:"):
                    try:
                        watermark = datetime.fromisoformat(last_log.api_response_status.split("watermark:")[1])
                    except Exception:
                        pass

                if watermark:
                    since = watermark - timedelta(hours=2)
                else:
                    latest_alloc = db.query(func.max(AmazonLiveAllocation.updated_at)).filter(
                        AmazonLiveAllocation.company_id == company_id
                    ).scalar()
                    if latest_alloc:
                        since = latest_alloc - timedelta(hours=2)
                    else:
                        since = datetime(2026, 8, 1)

        sync_log = AmazonSyncLog(
            company_id=company_id,
            order_id=f"SYNC-{int(time.time())}",
            sync_start_time=start_time,
            status="IN_PROGRESS",
            orders_processed=0,
            skipped_duplicates=0,
            failed_items=0,
            unknown_skus="[]"
        )
        db.add(sync_log)
        db.commit()
        db.refresh(sync_log)

        # 2. Pre-fetch existing order IDs to optimize line item fetches
        existing_order_tuples = db.query(AmazonLiveAllocation.order_id).filter(
            AmazonLiveAllocation.company_id == company_id
        ).distinct().all()
        existing_ids = {r[0] for r in existing_order_tuples if r[0]}

        # 3. Resolve warehouse mappings
        # MFN Warehouse: prefer MFN mapping for this company, or CENTRAL warehouse
        mfn_wh = db.query(Warehouse).join(
            WarehouseExternalMapping, Warehouse.id == WarehouseExternalMapping.warehouse_id
        ).filter(
            Warehouse.company_id == company_id,
            WarehouseExternalMapping.amazon_network == AmazonNetworkType.MFN,
            Warehouse.status == "ACTIVE"
        ).first()

        if not mfn_wh:
            mfn_wh = db.query(Warehouse).filter(
                Warehouse.company_id == company_id,
                Warehouse.status == "ACTIVE"
            ).first()

        mfn_warehouse_id = mfn_wh.id if mfn_wh else None

        # AFN Warehouse: default AFN mapping or fallback
        afn_wh = db.query(Warehouse).join(
            WarehouseExternalMapping, Warehouse.id == WarehouseExternalMapping.warehouse_id
        ).filter(
            Warehouse.company_id == company_id,
            WarehouseExternalMapping.amazon_network == AmazonNetworkType.AFN,
            Warehouse.status == "ACTIVE"
        ).first()

        afn_warehouse_id = afn_wh.id if afn_wh else mfn_warehouse_id

        # Cache products for fast in-memory lookup
        products = db.query(Product.sku).filter(Product.company_id == company_id).all()
        known_skus = {p.sku.upper() for p in products if p.sku}

        # Status Map
        status_map = {
            "Pending": AllocationStatus.PENDING,
            "Unshipped": AllocationStatus.UNSHIPPED,
            "PartiallyShipped": AllocationStatus.UNSHIPPED,
            "Shipped": AllocationStatus.SHIPPED,
            "Canceled": AllocationStatus.CANCELLED,
            "InvoiceUnconfirmed": AllocationStatus.UNSHIPPED
        }

        counters = {
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "unknown_skus": set()
        }

        def process_page(orders_page: List[Dict[str, Any]]):
            for order in orders_page:
                order_id = order.get("order_id")
                amazon_status = order.get("status")
                channel = order.get("fulfillment_channel", "MFN")
                last_update_str = order.get("last_update_date")
                
                try:
                    last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00")).replace(tzinfo=None) if last_update_str else datetime.utcnow()
                except Exception:
                    last_update = datetime.utcnow()

                if "max_order_date" not in counters or (last_update and last_update > counters["max_order_date"]):
                    counters["max_order_date"] = last_update

                mapped_status = status_map.get(amazon_status, AllocationStatus.PENDING)
                network = AmazonNetworkType.MFN if channel == "MFN" else AmazonNetworkType.AFN
                target_warehouse_id = mfn_warehouse_id if network == AmazonNetworkType.MFN else afn_warehouse_id

                # If this order was already known and had no items fetched
                if order.get("is_known_order") and not order.get("items"):
                    existing_allocations = db.query(AmazonLiveAllocation).filter(
                        AmazonLiveAllocation.order_id == order_id,
                        AmazonLiveAllocation.company_id == company_id
                    ).all()

                    status_changed = False
                    for alloc in existing_allocations:
                        if alloc.status != mapped_status:
                            prev_status = alloc.status
                            alloc.status = mapped_status
                            alloc.updated_at = last_update
                            if mapped_status == AllocationStatus.CANCELLED:
                                alloc.closed = True
                                alloc.allocated_qty = alloc.reconciled_qty
                            
                            event = AmazonOrderEventLog(
                                allocation_id=alloc.id,
                                previous_status=prev_status.value,
                                new_status=mapped_status.value,
                                timestamp=datetime.utcnow()
                            )
                            db.add(event)
                            status_changed = True
                    
                    if status_changed:
                        counters["processed"] += 1
                    else:
                        counters["skipped"] += 1
                    continue

                # Process order items for new or itemized orders
                for item in order.get("items", []):
                    sku = str(item.get("sku", "")).strip().upper()
                    line_item_id = str(item.get("amazon_line_item_id", "default"))
                    qty = int(item.get("quantity") or 0)

                    if not sku:
                        continue

                    if sku not in known_skus:
                        # Quarantine in DLQ
                        dlq = AmazonDLQ(
                            company_id=company_id,
                            dlq_type=DLQType.DATA_MISMATCH,
                            reference_id=order_id,
                            error_message=f"Unknown SKU: {sku}",
                            payload={"item": item, "order_id": order_id, "channel": channel}
                        )
                        db.add(dlq)
                        counters["failed"] += 1
                        counters["unknown_skus"].add(sku)
                        continue

                    try:
                        with db.begin_nested():
                            existing = db.query(AmazonLiveAllocation).filter(
                                AmazonLiveAllocation.order_id == order_id,
                                AmazonLiveAllocation.sku == sku,
                                AmazonLiveAllocation.amazon_line_item_id == line_item_id
                            ).with_for_update().first()

                            if existing:
                                if existing.updated_at and existing.updated_at >= last_update:
                                    counters["skipped"] += 1
                                    continue

                                if existing.status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]:
                                    counters["skipped"] += 1
                                    continue

                                prev_status = existing.status
                                existing.status = mapped_status
                                existing.allocated_qty = qty
                                existing.updated_at = last_update

                                if mapped_status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]:
                                    existing.closed = True
                                    existing.allocated_qty = existing.reconciled_qty

                                if prev_status != mapped_status:
                                    event = AmazonOrderEventLog(
                                        allocation_id=existing.id,
                                        previous_status=prev_status.value,
                                        new_status=mapped_status.value,
                                        timestamp=datetime.utcnow()
                                    )
                                    db.add(event)
                                counters["processed"] += 1
                            else:
                                closed = mapped_status in [AllocationStatus.CANCELLED, AllocationStatus.RETURNED, AllocationStatus.REFUNDED]
                                final_qty = 0 if closed else qty

                                allocation = AmazonLiveAllocation(
                                    company_id=company_id,
                                    order_id=order_id,
                                    sku=sku,
                                    amazon_line_item_id=line_item_id,
                                    warehouse_id=target_warehouse_id,
                                    amazon_network_at_allocation=network,
                                    allocated_qty=final_qty,
                                    status=mapped_status,
                                    closed=closed,
                                    updated_at=last_update
                                )
                                db.add(allocation)
                                db.flush()

                                event = AmazonOrderEventLog(
                                    allocation_id=allocation.id,
                                    previous_status=None,
                                    new_status=mapped_status.value,
                                    timestamp=datetime.utcnow()
                                )
                                db.add(event)
                                counters["processed"] += 1
                                existing_ids.add(order_id)
                    except Exception as item_err:
                        logger.error(f"Failed processing item {sku} on order {order_id}: {item_err}")
                        counters["failed"] += 1

            # Commit after each page with live telemetry
            sync_log.orders_processed = counters["processed"]
            sync_log.skipped_duplicates = counters["skipped"]
            sync_log.failed_items = counters["failed"]
            sync_log.unknown_skus = json.dumps(list(counters["unknown_skus"]))
            db.commit()

        try:
            client.fetch_orders(
                since=since,
                existing_order_ids=existing_ids,
                on_page_callback=process_page,
                max_pages=max_pages
            )

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            sync_log.status = "SUCCESS"
            sync_log.sync_end_time = end_time
            sync_log.orders_processed = counters["processed"]
            sync_log.skipped_duplicates = counters["skipped"]
            sync_log.failed_items = counters["failed"]
            watermark_ts = end_time if not max_pages else counters.get("max_order_date", end_time)
            sync_log.api_response_status = f"watermark:{watermark_ts.isoformat()}"
            db.commit()

            return {
                "status": "SUCCESS",
                "since": since.isoformat(),
                "orders_processed": counters["processed"],
                "skipped_duplicates": counters["skipped"],
                "failed_items": counters["failed"],
                "unknown_skus": list(counters["unknown_skus"]),
                "duration_seconds": round(duration, 2)
            }
        except Exception as sync_err:
            logger.error(f"Amazon sync failed: {sync_err}", exc_info=True)
            sync_log.status = "FAILED"
            sync_log.sync_end_time = datetime.utcnow()
            sync_log.errors = str(sync_err)
            db.commit()
            raise sync_err

    @staticmethod
    def poll_orders(db: Session, company_id: int, since=None) -> Tuple[int, int]:
        """
        Backwards-compatible polling entry point for scheduler and CLI.
        """
        res = AmazonService.sync_orders(db, company_id=company_id, since=since)
        return res.get("orders_processed", 0), res.get("skipped_duplicates", 0)
