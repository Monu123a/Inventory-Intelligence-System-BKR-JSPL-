from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.db import get_db
from app.models.schema import AmazonReturn, DefectiveInventory, User
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/reports/returns", tags=["Returns Reports"])

@router.get("/metrics")
def get_return_metrics(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    today = datetime.utcnow().date()
    
    # Returns Today
    returns_today = db.query(AmazonReturn).filter(
        AmazonReturn.company_id == company_id,
        func.date(AmazonReturn.created_at) == today
    ).count()
    
    # Awaiting Inspection
    awaiting_inspection = db.query(AmazonReturn).filter(
        AmazonReturn.company_id == company_id,
        AmazonReturn.return_status == "Received",
        AmazonReturn.inspection_status.is_(None)
    ).count()
    
    # Restocked
    restocked = db.query(AmazonReturn).filter(
        AmazonReturn.company_id == company_id,
        AmazonReturn.inspection_status == "RESTOCKED"
    ).count()
    
    # Defective
    defective = db.query(AmazonReturn).filter(
        AmazonReturn.company_id == company_id,
        AmazonReturn.inspection_status == "DEFECTIVE"
    ).count()
    
    # Inspection Pending > 2 Days (SQL filter instead of Python loop)
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    pending_count = db.query(AmazonReturn).filter(
        AmazonReturn.company_id == company_id,
        AmazonReturn.return_status == "Received",
        AmazonReturn.inspection_status.is_(None),
        AmazonReturn.received_at < two_days_ago
    ).count()

    return {
        "returns_today": returns_today,
        "awaiting_inspection": awaiting_inspection,
        "restocked": restocked,
        "defective": defective,
        "inspection_pending_old": pending_count
    }

@router.get("/amazon-returns")
def amazon_returns_report(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    returns = db.query(AmazonReturn, User.username.label('inspector_name')).outerjoin(
        User, AmazonReturn.inspected_by == User.id
    ).filter(AmazonReturn.company_id == company_id).all()
    
    return {
        "data": [
            {
                "return_id": r.AmazonReturn.amazon_return_id,
                "sku": r.AmazonReturn.sku,
                "product": r.AmazonReturn.product_name,
                "reason": r.AmazonReturn.return_reason,
                "inspection_status": r.AmazonReturn.inspection_status or "Pending",
                "inspector": r.inspector_name,
                "date": r.AmazonReturn.requested_at
            } for r in returns
        ]
    }

@router.get("/defective-inventory")
def defective_inventory_report(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    defectives = db.query(DefectiveInventory).filter(
        DefectiveInventory.company_id == company_id
    ).all()
    
    return {
        "data": [
            {
                "sku": d.sku_snapshot,
                "product": d.product_name_snapshot,
                "defect_status": d.status,
                "quantity": d.quantity,
                "inspection_date": d.inspection_date
            } for d in defectives
        ]
    }
