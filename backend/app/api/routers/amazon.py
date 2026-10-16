from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
import json
import logging

from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user
from app.models.schema import (
    AmazonLiveAllocation, AmazonSyncLog, AmazonDLQ, User, 
    Warehouse, WarehouseExternalMapping, AmazonNetworkType, Inventory
)
from app.services.amazon_service import AmazonService
from app.services.amazon_client import get_amazon_client
from app.services.amazon_reconciliation_service import AmazonReconciliationService

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


def run_background_fc_shipment_reconciliation(company_id: int, start_date: datetime, end_date: datetime):
    from app.models.db import SessionLocal
    sync_db = SessionLocal()
    try:
        logger.info(f"Starting automated SP-API shipment report pull for company {company_id}...")
        client = get_amazon_client()
        if not hasattr(client, "request_and_download_shipment_report"):
            logger.error("Client does not support request_and_download_shipment_report")
            return
            
        doc_content = client.request_and_download_shipment_report(start_date=start_date, end_date=end_date)
        res = AmazonReconciliationService.reconcile_fc_shipment_report(
            db=sync_db,
            company_id=company_id,
            report_data=doc_content,
            allow_negative_stock=True
        )
        logger.info(f"FC shipment reconciliation completed: {res}")
    except Exception as e:
        logger.error(f"FC shipment reconciliation failed: {e}", exc_info=True)
    finally:
        sync_db.close()


@router.post("/request-fc-shipments")
def request_fc_shipments(
    background_tasks: BackgroundTasks,
    days_back: int = Query(7, description="Number of past days of shipments to reconcile"),
    async_mode: bool = Query(True, description="Run in background"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Requests Amazon Fulfilled Shipments Report via SP-API Reports API, downloads it,
    and deducts physical inventory from the respective FC warehouses.
    """
    from datetime import timedelta
    start_dt = datetime.utcnow() - timedelta(days=days_back)
    end_dt = datetime.utcnow()

    if async_mode:
        background_tasks.add_task(run_background_fc_shipment_reconciliation, company_id, start_dt, end_dt)
        return {
            "message": f"Amazon Fulfilled Shipments Report requested for the past {days_back} days. Processing and FC inventory deduction running in background.",
            "status": "IN_PROGRESS"
        }

    try:
        client = get_amazon_client()
        doc_content = client.request_and_download_shipment_report(start_date=start_dt, end_date=end_dt)
        res = AmazonReconciliationService.reconcile_fc_shipment_report(
            db=db,
            company_id=company_id,
            report_data=doc_content,
            allow_negative_stock=True
        )
        return {
            "message": "FC shipment reconciliation completed successfully",
            "details": res
        }
    except Exception as e:
        logger.error(f"Manual FC shipment reconciliation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-fc-shipments")
async def upload_fc_shipments(
    file: UploadFile = File(...),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Manual upload of an Amazon Fulfilled Shipments Report or Settlement Report (CSV, TSV, XLSX).
    Parses FC codes and deducts inventory from the respective FC warehouses.
    """
    content = await file.read()
    try:
        if file.filename.endswith(".xlsx") or file.filename.endswith(".xls"):
            import pandas as pd
            import io
            df = pd.read_excel(io.BytesIO(content))
            res = AmazonReconciliationService.reconcile_fc_shipment_report(db, company_id, df)
        else:
            res = AmazonReconciliationService.reconcile_fc_shipment_report(db, company_id, content)

        return {
            "message": "Shipment report processed successfully",
            "details": res
        }
    except Exception as e:
        logger.error(f"Failed processing uploaded shipment file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed processing file: {str(e)}")


@router.get("/fc-inventory-summary")
def get_fc_inventory_summary(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """
    Returns live physical stock, available units, and active soft allocations across all Amazon FCs.
    """
    fc_warehouses = db.query(Warehouse).join(
        WarehouseExternalMapping, Warehouse.id == WarehouseExternalMapping.warehouse_id
    ).filter(
        Warehouse.company_id == company_id,
        WarehouseExternalMapping.amazon_network == AmazonNetworkType.AFN
    ).order_by(Warehouse.code.asc()).all()

    summary = []
    for wh in fc_warehouses:
        total_skus = db.query(func.count(Inventory.id)).filter(
            Inventory.company_id == company_id,
            Inventory.warehouse_id == wh.id,
            Inventory.current_qty > 0
        ).scalar() or 0

        physical_units = db.query(func.sum(Inventory.current_qty)).filter(
            Inventory.company_id == company_id,
            Inventory.warehouse_id == wh.id
        ).scalar() or 0

        available_units = db.query(func.sum(Inventory.available_qty)).filter(
            Inventory.company_id == company_id,
            Inventory.warehouse_id == wh.id
        ).scalar() or 0

        # Active allocations assigned to this FC
        active_allocs = db.query(func.sum(AmazonLiveAllocation.allocated_qty - AmazonLiveAllocation.reconciled_qty)).filter(
            AmazonLiveAllocation.company_id == company_id,
            AmazonLiveAllocation.warehouse_id == wh.id,
            AmazonLiveAllocation.closed == False
        ).scalar() or 0

        summary.append({
            "warehouse_id": wh.id,
            "fc_code": wh.code,
            "name": wh.name,
            "total_skus": total_skus,
            "physical_units": int(physical_units),
            "available_units": int(available_units),
            "active_allocations": int(active_allocs)
        })

    return summary
