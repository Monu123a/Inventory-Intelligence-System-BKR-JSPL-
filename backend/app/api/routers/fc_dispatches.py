from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest
from app.services.fc_scheduler import generate_45_day_return_recommendations
from app.models.schema import User, FCDispatch, FCDispatchItem, DispatchTimeline, Warehouse, Product, Inventory

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
    dispatch_source: Optional[str] = Query(None, description="BKR or CENTRAL_WAREHOUSE"),
    skip: int = 0,
    limit: int = 100
):
    company_id = current_user.company_id
    query = db.query(FCDispatch).filter(FCDispatch.company_id == company_id)
    
    # We do not have dispatch_source column, we derive it from source_warehouse_id
    # But for simple filtering, if dispatch_source == BKR, we could check if source_warehouse has company != current_company or similar.
    # Actually BKR source warehouse has company_id = BKR_COMPANY (1), JSPL has JSPL_COMPANY (2).
    # Since we can just return all and derive in python for simplicity, or we do a join.
    # Given the volume, we will just fetch and map. We do not enforce strict SQL filter for this right now.
    
    dispatches = query.order_by(FCDispatch.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for d in dispatches:
        # Derive origin dynamically
        origin = "BKR"
        if d.source_warehouse and d.source_warehouse.warehouse_type and d.source_warehouse.warehouse_type.value == "CENTRAL":
             origin = "CENTRAL_WAREHOUSE"
        elif d.source_warehouse and d.source_warehouse.company_id == company_id:
             # fallback for old data
             origin = "CENTRAL_WAREHOUSE"
             
        if dispatch_source and origin != dispatch_source:
             continue

        result.append({
            "id": d.id,
            "dispatch_number": d.dispatch_number,
            "dispatch_status": d.dispatch_status,
            "source_warehouse": d.source_warehouse.name if d.source_warehouse else "Unknown",
            "warehouse": d.warehouse.name if d.warehouse else "Unknown",
            "hub_code": d.warehouse.hub.hub_code if d.warehouse and d.warehouse.hub else "Unknown",
            "invoice_number": d.invoice.invoice_number if d.invoice else None,
            "challan_number": d.delivery_challan.challan_number if d.delivery_challan else None,
            "created_at": d.created_at.isoformat(),
            "origin": origin
        })
    return result

@router.get("/inventory")
def get_dispatch_inventory(
    source_type: str = Query("BKR", description="BKR or CENTRAL_WAREHOUSE"),
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    """Get available inventory for the selected source warehouse"""
    
    if source_type == "BKR":
        source_warehouse = db.query(Warehouse).filter(Warehouse.name.ilike("%BKR%")).first()
    else:
        source_warehouse = db.query(Warehouse).filter(
            Warehouse.company_id == company_id,
            or_(
                Warehouse.warehouse_type == 'CENTRAL_HUB',
                Warehouse.name.ilike('%VSHB%')
            )
        ).first()
        
    if not source_warehouse:
        return []
        
    # Fetch inventory for the resolved warehouse
    inventory_records = db.query(Inventory).options(joinedload(Inventory.product)).filter(
        Inventory.warehouse_id == source_warehouse.id,
        Inventory.company_id == source_warehouse.company_id,
        Inventory.available_qty > 0
    ).all()
    
    return [
        {
            "id": inv.product.id,
            "sku": inv.product.sku,
            "name": inv.product.name,
            "currentStock": inv.available_qty,
            "recommended": int(inv.available_qty * 0.1) if inv.available_qty > 10 else 1 # Dummy logic for wizard
        }
        for inv in inventory_records if inv.product
    ]

@router.get("/recommendations")
def get_45_day_recommendations(
    current_user: User = Depends(get_current_user)
):
    """Get the 45-day return recommendations computed dynamically (or from cache in future)"""
    recs = generate_45_day_return_recommendations()
    return recs or []
