from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
import json
import logging

from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user
from app.models.schema import AmazonLiveAllocation, AmazonSyncLog, AmazonDLQ, User
from app.services.amazon_service import AmazonService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/amazon", tags=["amazon"])

@router.get("/live-inventory")
def get_live_inventory(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    # Group by SKU and Amazon Network
    allocations = db.query(
        AmazonLiveAllocation.sku,
        AmazonLiveAllocation.amazon_network_at_allocation,
        func.sum(AmazonLiveAllocation.allocated_qty).label("total_allocated"),
        func.sum(AmazonLiveAllocation.reconciled_qty).label("total_reconciled"),
        func.count(AmazonLiveAllocation.id).label("active_orders")
    ).filter(
        AmazonLiveAllocation.company_id == company_id,
        AmazonLiveAllocation.closed == False
    ).group_by(
        AmazonLiveAllocation.sku,
        AmazonLiveAllocation.amazon_network_at_allocation
    ).all()
    
    result = []
    for a in allocations:
        result.append({
            "sku": a.sku,
            "network": a.amazon_network_at_allocation.value if a.amazon_network_at_allocation else "UNMAPPED",
            "allocated_qty": a.total_allocated or 0,
            "reconciled_qty": a.total_reconciled or 0,
            "pending_qty": (a.total_allocated or 0) - (a.total_reconciled or 0),
            "active_orders": a.active_orders or 0
        })
    return result


@router.get("/sync-status")
def get_sync_status(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns latest sync telemetry, running status, and health metrics.
    """
    latest_log = db.query(AmazonSyncLog).filter(
        AmazonSyncLog.company_id == company_id
    ).order_by(AmazonSyncLog.id.desc()).first()

    active_allocations_count = db.query(AmazonLiveAllocation).filter(
        AmazonLiveAllocation.company_id == company_id,
        AmazonLiveAllocation.closed == False
    ).count()

    active_orders_count = db.query(AmazonLiveAllocation.order_id).filter(
        AmazonLiveAllocation.company_id == company_id,
        AmazonLiveAllocation.closed == False
    ).distinct().count()

    dlq_count = db.query(AmazonDLQ).filter(
        AmazonDLQ.company_id == company_id
    ).count()

    unknown_skus = []
    if latest_log and latest_log.unknown_skus:
        try:
            unknown_skus = json.loads(latest_log.unknown_skus)
        except Exception:
            unknown_skus = []

    return {
        "status": latest_log.status if latest_log else "NEVER_RUN",
        "last_sync_start": latest_log.sync_start_time.isoformat() if latest_log and latest_log.sync_start_time else None,
        "last_sync_end": latest_log.sync_end_time.isoformat() if latest_log and latest_log.sync_end_time else None,
        "orders_processed": latest_log.orders_processed if latest_log else 0,
        "skipped_duplicates": latest_log.skipped_duplicates if latest_log else 0,
        "failed_items": latest_log.failed_items if latest_log else 0,
        "unknown_skus": unknown_skus,
        "error_message": latest_log.errors if latest_log else None,
        "active_allocations_count": active_allocations_count,
        "active_orders_count": active_orders_count,
        "dlq_count": dlq_count
    }


def run_background_sync(company_id: int, since_dt: Optional[datetime], force_backfill: bool, max_pages: Optional[int]):
    from app.models.db import SessionLocal
    sync_db = SessionLocal()
    try:
        logger.info(f"Starting background Amazon sync for company {company_id}...")
        AmazonService.sync_orders(
            db=sync_db,
            company_id=company_id,
            since=since_dt,
            force_backfill=force_backfill,
            max_pages=max_pages
        )
        logger.info(f"Background Amazon sync completed for company {company_id}.")
    except Exception as e:
        logger.error(f"Background Amazon sync failed for company {company_id}: {e}", exc_info=True)
    finally:
        sync_db.close()


@router.post("/sync")
def trigger_amazon_sync(
    background_tasks: BackgroundTasks,
    backfill: bool = Query(False, description="Set to true for full backfill from August 1, 2026"),
    since: Optional[str] = Query(None, description="Custom ISO start date (e.g. 2026-08-01)"),
    max_pages: Optional[int] = Query(None, description="Max pages to fetch in this batch"),
    async_mode: bool = Query(True, description="Run in background to prevent HTTP timeouts"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Triggers an Amazon SP-API Order synchronization (runs asynchronously in background by default).
    """
    from datetime import timedelta
    
    # Check if a sync is already actively running in the last 20 minutes
    active_sync = db.query(AmazonSyncLog).filter(
        AmazonSyncLog.company_id == company_id,
        AmazonSyncLog.status == "IN_PROGRESS",
        AmazonSyncLog.sync_start_time >= datetime.utcnow() - timedelta(minutes=20)
    ).first()

    if active_sync:
        return {
            "message": "An Amazon sync is already running in the background.",
            "status": "IN_PROGRESS",
            "sync_id": active_sync.order_id
        }

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'since' date format. Use ISO format (YYYY-MM-DD).")

    if async_mode:
        background_tasks.add_task(run_background_sync, company_id, since_dt, backfill, max_pages)
        return {
            "message": "Amazon sync has been started in the background. Monitor status via /sync-status.",
            "status": "IN_PROGRESS"
        }

    try:
        result = AmazonService.sync_orders(
            db=db,
            company_id=company_id,
            since=since_dt,
            force_backfill=backfill,
            max_pages=max_pages
        )
        return {
            "message": "Amazon sync completed successfully",
            "details": result
        }
    except Exception as e:
        logger.error(f"Manual Amazon sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Amazon sync failed: {str(e)}")


@router.get("/dlq")
def get_amazon_dlq_records(
    limit: int = 50,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """
    Returns quarantined items from the Dead Letter Queue (e.g. unknown SKUs).
    """
    records = db.query(AmazonDLQ).filter(
        AmazonDLQ.company_id == company_id
    ).order_by(AmazonDLQ.id.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "order_id": r.reference_id,
            "dlq_type": r.dlq_type.value if hasattr(r.dlq_type, 'value') else str(r.dlq_type),
            "error_message": r.error_message,
            "payload": r.payload,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
