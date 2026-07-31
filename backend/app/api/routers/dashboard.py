from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import Dict, Any, List

from app.models.db import get_db
from app.models.schema import Company, Product, Warehouse, Inventory, InventoryMovement, AmazonSyncLog, ReportHistory, Alert, JobExecutionLog, Sale, SaleItem
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
    today = date.today()
    
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
        func.date(InventoryMovement.timestamp) == today
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
            func.date(Sale.sale_date) == today
        ).scalar() or 0
        
        pos_sales_count_today = db.query(Sale).filter(
            Sale.company_id == company_id,
            Sale.status == "Completed",
            func.date(Sale.sale_date) == today
        ).count()
        
        pos_products_sold_today = db.query(func.sum(SaleItem.quantity)).join(Sale).filter(
            Sale.company_id == company_id,
            Sale.status == "Completed",
            func.date(Sale.sale_date) == today
        ).scalar() or 0

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
            "pos_products_sold_today": pos_products_sold_today
        },
        "health": {
            "amazon_sync": amazon_sync_data,
            "latest_inventory_upload": latest_inventory_upload.timestamp.isoformat() if latest_inventory_upload else None,
            "scheduler_status": scheduler_status,
            "last_snapshot_time": latest_snapshot_job.start_time.isoformat() if latest_snapshot_job else None,
            "last_replenishment_report": latest_report_job.start_time.isoformat() if latest_report_job else None,
        }
    }

@router.get("/activity")
def get_recent_activity(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns latest activities for the dashboard activity feed with presentation metadata.
    """
    movements = db.query(InventoryMovement).filter(InventoryMovement.company_id == company_id).order_by(InventoryMovement.timestamp.desc()).limit(10).all()
    
    activity_feed = []
    for mov in movements:
        desc = ""
        if mov.source == "Amazon":
            desc = f"Amazon Order {mov.reference_id} processed for {mov.product_sku}"
        elif mov.source == "Upload":
            desc = f"Inventory updated via Excel upload for {mov.product_sku}"
        else:
            desc = f"Manual adjustment of {mov.qty_changed} for {mov.product_sku}"
            
        activity_feed.append({
            "id": mov.id,
            "timestamp": mov.timestamp,
            "type": mov.source,
            "description": desc,
            "status": "Success" if mov.qty_after >= 0 else "Warning",
            "metadata": {
                "sku": mov.product_sku,
                "qty_changed": mov.qty_changed
            }
        })
        
    return {
        "recent_activity": activity_feed
    }

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
