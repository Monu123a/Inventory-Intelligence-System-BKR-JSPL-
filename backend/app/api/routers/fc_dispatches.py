from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.auth.dependencies import get_current_user
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest
from app.services.fc_scheduler import generate_45_day_return_recommendations
from app.models.schema import User, FCDispatch

router = APIRouter(prefix="/fc-dispatches", tags=["FC Dispatches"])

@router.post("/")
def create_batch_dispatch(
    request: FCDispatchBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create single or batch dispatch to Fulfillment Centers"""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
        
    dispatches = FCDispatchService.create_batch_dispatch(db, company_id, request, current_user.id)
    return {"message": f"Successfully created {len(dispatches)} dispatches", "dispatches": [{"id": d.id, "dispatch_number": d.dispatch_number} for d in dispatches]}

@router.get("/")
def get_dispatches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    company_id = current_user.company_id
    dispatches = db.query(FCDispatch).filter(FCDispatch.company_id == company_id).order_by(FCDispatch.created_at.desc()).offset(skip).limit(limit).all()
    
    # In a real scenario we'd use a Pydantic response model to return nested relations
    # like warehouse name, invoice total, etc.
    result = []
    for d in dispatches:
        result.append({
            "id": d.id,
            "dispatch_number": d.dispatch_number,
            "dispatch_status": d.dispatch_status,
            "warehouse": d.warehouse.name if d.warehouse else "Unknown",
            "hub_code": d.warehouse.hub.hub_code if d.warehouse and d.warehouse.hub else "Unknown",
            "invoice_number": d.invoice.invoice_number if d.invoice else None,
            "challan_number": d.delivery_challan.challan_number if d.delivery_challan else None,
            "created_at": d.created_at.isoformat(),
        })
    return result

@router.get("/recommendations")
def get_45_day_recommendations(
    current_user: User = Depends(get_current_user)
):
    """Get the 45-day return recommendations computed dynamically (or from cache in future)"""
    recs = generate_45_day_return_recommendations()
    return recs or []
