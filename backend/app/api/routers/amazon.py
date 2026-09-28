from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.db import get_db
from app.api.dependencies import get_current_company_id
from app.models.schema import AmazonLiveAllocation

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
