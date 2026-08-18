from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

from app.models.db import get_db
from app.models.schema import (
    Company, Product, Warehouse, Inventory, InventoryMovement, AmazonSyncLog, 
    Alert, JobExecutionLog, Sale, SaleItem, SalesReturn, DeliveryChallan, FCDispatch,
    FCReturn, ServiceRecord
)
from app.models.accounting_schema import AccountingExportBatch
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_alert_severity(alert_type: str) -> str:
    alert_type_lower = alert_type.lower()
    if "negative" in alert_type_lower or "error" in alert_type_lower:
        return "CRITICAL"
    if "low" in alert_type_lower or "warning" in alert_type_lower:
        return "WARNING"
    return "INFO"

@router.get("/metrics")
def get_dashboard_metrics(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns KPI metrics and System Health for the Overview Dashboard.
    """
    today = date.today().isoformat()
    today_start = datetime.combine(date.today(), datetime.min.time())
    tomorrow_start = datetime.combine(date.today(), datetime.max.time())
    
    # KPI Metrics
    total_products = db.query(Product).filter(Product.company_id == company_id).count()
    total_warehouses = db.query(Warehouse).filter(Warehouse.company_id == company_id).count()
    total_inventory = db.query(func.sum(Inventory.current_qty)).filter(Inventory.company_id == company_id).scalar() or 0
    # Negative stock (sum across warehouses < 0)
    total_qty_subquery = db.query(
        Inventory.product_id, 
        func.sum(Inventory.current_qty).label("total_qty")
    ).filter(Inventory.company_id == company_id).group_by(Inventory.product_id).subquery()

    negative_stock_count = db.query(Product).filter(Product.company_id == company_id).outerjoin(
        total_qty_subquery, Product.id == total_qty_subquery.c.product_id
    ).filter(
        func.coalesce(total_qty_subquery.c.total_qty, 0) < 0
    ).count()

    # Low stock (sum across warehouses >= 0 but < min_stock_level)
    low_stock_count = db.query(Product).filter(Product.company_id == company_id).outerjoin(
        total_qty_subquery, Product.id == total_qty_subquery.c.product_id
    ).filter(
        func.coalesce(total_qty_subquery.c.total_qty, 0) >= 0,
        func.coalesce(total_qty_subquery.c.total_qty, 0) < Product.min_stock_level,
        Product.min_stock_level > 0 # only count if it actually HAS a minimum limit!
    ).count()
        
    today_updates = db.query(InventoryMovement).filter(
        InventoryMovement.company_id == company_id,
        InventoryMovement.timestamp >= today_start, InventoryMovement.timestamp <= tomorrow_start
    ).count()
    
    active_alerts = db.query(Alert).filter(Alert.company_id == company_id, Alert.is_resolved == False).count()

    # System Health Information
    latest_amazon_sync = db.query(AmazonSyncLog).filter(AmazonSyncLog.company_id == company_id).order_by(AmazonSyncLog.sync_start_time.desc()).first()
    latest_inventory_upload = db.query(InventoryMovement).filter(InventoryMovement.company_id == company_id, InventoryMovement.source == "Upload").order_by(InventoryMovement.timestamp.desc()).first()
    latest_snapshot_job = db.query(JobExecutionLog).filter(
        JobExecutionLog.company_id == company_id,
        JobExecutionLog.job_name.like("Midnight Snapshot%")
    ).order_by(JobExecutionLog.start_time.desc()).first()
    latest_report_job = db.query(JobExecutionLog).filter(
        JobExecutionLog.company_id == company_id,
        JobExecutionLog.job_name.like("Daily Replenishment Report%")
    ).order_by(JobExecutionLog.start_time.desc()).first()
    
    # Check if there are any running/failed scheduler jobs recently
    recent_jobs = db.query(JobExecutionLog).filter(JobExecutionLog.company_id == company_id).order_by(JobExecutionLog.start_time.desc()).limit(10).all()
    scheduler_status = "Healthy"
    if any(job.status == "Failed" for job in recent_jobs):
        scheduler_status = "Warning"
        
    amazon_sync_data = None
    if latest_amazon_sync:
        amazon_sync_data = {
            "sync_start_time": latest_amazon_sync.sync_start_time.isoformat() if latest_amazon_sync.sync_start_time else None,
            "status": latest_amazon_sync.status,
            "orders_processed": latest_amazon_sync.orders_processed,
            "movements_created": latest_amazon_sync.movements_created,
            "skipped_duplicates": latest_amazon_sync.skipped_duplicates,
            "failed_items": latest_amazon_sync.failed_items,
            "unknown_skus": latest_amazon_sync.unknown_skus,
            "next_token": latest_amazon_sync.next_token,
            "errors": latest_amazon_sync.errors
        }

    # POS Metrics (BKR Only)
    pos_revenue_today = 0
    pos_sales_count_today = 0
    pos_products_sold_today = 0
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if company and company.code == "BKR":
        pos_revenue_today = db.query(func.sum(Sale.grand_total)).filter(
            Sale.company_id == company_id,
            Sale.status == "Completed",
            Sale.sale_date >= today_start, Sale.sale_date <= tomorrow_start
        ).scalar() or 0
        
        pos_sales_count_today = db.query(Sale).filter(
            Sale.company_id == company_id,
            Sale.status == "Completed",
            Sale.sale_date >= today_start, Sale.sale_date <= tomorrow_start
        ).count()
        
        pos_products_sold_today = db.query(func.sum(SaleItem.quantity)).join(Sale).filter(
            Sale.company_id == company_id,
            Sale.status == "Completed",
            Sale.sale_date >= today_start, Sale.sale_date <= tomorrow_start
        ).scalar() or 0

    sales_returns_today = db.query(SalesReturn).filter(
        SalesReturn.company_id == company_id,
        SalesReturn.status == 'Completed',
        SalesReturn.created_at >= today_start, SalesReturn.created_at <= tomorrow_start
    ).count()

    sales_return_value_today = db.query(func.sum(SalesReturn.grand_total)).filter(
        SalesReturn.company_id == company_id,
        SalesReturn.status == 'Completed',
        SalesReturn.created_at >= today_start, SalesReturn.created_at <= tomorrow_start
    ).scalar() or 0.0

    pending_sales_returns = db.query(SalesReturn).filter(
        SalesReturn.company_id == company_id,
        SalesReturn.status == 'Draft'
    ).count()

    challans_today = db.query(DeliveryChallan).filter(
        DeliveryChallan.company_id == company_id,
        DeliveryChallan.created_at >= today_start, DeliveryChallan.created_at <= tomorrow_start
    ).count()

    pending_dispatches = db.query(FCDispatch).filter(
        FCDispatch.company_id == company_id,
        FCDispatch.dispatch_status == 'DRAFT'
    ).count()

    failed_amazon_syncs = db.query(AmazonSyncLog).filter(
        AmazonSyncLog.company_id == company_id,
        AmazonSyncLog.status == 'FAILED'
    ).count()

    pending_accounting_exports = db.query(AccountingExportBatch).filter(
        AccountingExportBatch.company_id == company_id,
        AccountingExportBatch.status == 'PENDING'
    ).count() if (company and company.code == "BKR") else 0

    return {
        "kpis": {
            "total_products": total_products,
            "total_warehouses": total_warehouses,
            "total_inventory": total_inventory,
            "negative_stock_products": negative_stock_count,
            "low_stock_products": low_stock_count,
            "todays_inventory_updates": today_updates,
            "active_alerts": active_alerts,
            "pos_revenue_today": pos_revenue_today,
            "pos_sales_count_today": pos_sales_count_today,
            "pos_products_sold_today": pos_products_sold_today,
            "sales_returns_today": sales_returns_today,
            "sales_return_value_today": sales_return_value_today,
            "pending_sales_returns": pending_sales_returns,
            "challans_today": challans_today,
            "pending_dispatches": pending_dispatches,
            "failed_amazon_syncs": failed_amazon_syncs,
            "pending_accounting_exports": pending_accounting_exports
        },
        "health": {
            "amazon_sync": amazon_sync_data,
            "latest_inventory_upload": latest_inventory_upload.timestamp.isoformat() if latest_inventory_upload else None,
            "scheduler_status": scheduler_status,
            "last_snapshot_time": latest_snapshot_job.start_time.isoformat() if latest_snapshot_job and latest_snapshot_job.start_time else None,
            "last_replenishment_report": latest_report_job.start_time.isoformat() if latest_report_job and latest_report_job.start_time else None,
        }
    }

@router.get("/activity")
def get_recent_activity(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns latest activities for the dashboard activity feed across multiple operational tables.
    """
    activity_feed = []

    # 1. Inventory Uploads
    uploads = db.query(InventoryMovement).filter(
        InventoryMovement.company_id == company_id,
        InventoryMovement.source == 'Upload'
    ).order_by(InventoryMovement.timestamp.desc()).limit(5).all()
    for u in uploads:
        activity_feed.append({
            "id": f"inv_{u.id}", "timestamp": u.timestamp, "type": "Inventory Upload",
            "description": f"Inventory updated via Excel upload for {u.product_sku}",
            "status": "Success", "metadata": {"sku": u.product_sku, "qty_changed": u.qty_changed}
        })

    # 2. Dispatch Created
    dispatches = db.query(FCDispatch).filter(FCDispatch.company_id == company_id).order_by(FCDispatch.created_at.desc()).limit(5).all()
    for d in dispatches:
        activity_feed.append({
            "id": f"disp_{d.id}", "timestamp": d.created_at, "type": "Dispatch Created",
            "description": f"Dispatch {d.dispatch_number} created",
            "status": "Success", "metadata": {"dispatch_number": d.dispatch_number}
        })

    # 3. Return Completed
    returns = db.query(FCReturn).filter(FCReturn.company_id == company_id, FCReturn.status == 'COMPLETED').order_by(FCReturn.created_at.desc()).limit(5).all()
    for r in returns:
        activity_feed.append({
            "id": f"ret_{r.id}", "timestamp": r.created_at, "type": "Return Completed",
            "description": f"Return {r.return_number} marked as completed",
            "status": "Success", "metadata": {"return_number": r.return_number}
        })

    # 4. Amazon Sync
    syncs = db.query(AmazonSyncLog).filter(AmazonSyncLog.company_id == company_id).order_by(AmazonSyncLog.sync_start_time.desc()).limit(5).all()
    for s in syncs:
        activity_feed.append({
            "id": f"sync_{s.id}", "timestamp": s.sync_start_time, "type": "Amazon Sync",
            "description": f"Amazon Sync: {s.orders_processed} orders processed",
            "status": "Success" if s.status == 'SUCCESS' else "Warning", "metadata": {"status": s.status}
        })

    # 5. Service Completed
    services = db.query(ServiceRecord).filter(ServiceRecord.company_id == company_id, ServiceRecord.status == 'Completed').order_by(ServiceRecord.created_at.desc()).limit(5).all()
    for s in services:
        activity_feed.append({
            "id": f"srv_{s.id}", "timestamp": s.created_at, "type": "Service Completed",
            "description": f"Service {s.service_number} completed for {s.customer_name_snapshot}",
            "status": "Success", "metadata": {"service_number": s.service_number}
        })

    # Sort all by timestamp descending and take top 15
    activity_feed.sort(key=lambda x: x["timestamp"], reverse=True)
    activity_feed = activity_feed[:15]

    return {"recent_activity": activity_feed}

@router.get("/alerts")
def get_active_alerts(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns active alerts for the dashboard with severity.
    """
    recent_alerts = db.query(Alert).filter(Alert.company_id == company_id, Alert.is_resolved == False).order_by(Alert.timestamp.desc()).limit(10).all()
    alerts_feed = [
        {
            "id": a.id, 
            "type": a.alert_type, 
            "message": a.message, 
            "timestamp": a.timestamp,
            "resolved": a.is_resolved,
            "severity": get_alert_severity(a.alert_type)
        } for a in recent_alerts
    ]
    return {"recent_alerts": alerts_feed}

@router.put("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.company_id == company_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.is_resolved = True
    db.commit()
    return {"message": "Alert marked as resolved", "id": alert_id}
