from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest
from app.services.fc_scheduler import generate_45_day_return_recommendations
from app.models.schema import User, FCDispatch, Warehouse, Inventory

router = APIRouter(prefix="/fc-dispatches", tags=["FC Dispatches"])

@router.post("/")
def create_batch_dispatch(
    request: FCDispatchBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id)
):
    """Create single or batch dispatch to Fulfillment Centers"""
        
    try:
        dispatches = FCDispatchService.create_batch_dispatch(db, company_id, request, current_user.id)
        db.commit()
        return {"message": f"Successfully created {len(dispatches)} dispatches", "dispatches": [{"id": d.id, "dispatch_number": d.dispatch_number} for d in dispatches]}
    except HTTPException:
        db.rollback()
        raise
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while creating the dispatch.")

@router.get("/")
def get_dispatches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id),
    dispatch_type: Optional[str] = Query(None, description="STANDARD or EMERGENCY"),
    source_warehouse_id: Optional[int] = Query(None, description="Filter by source warehouse"),
    skip: int = 0,
    limit: int = 100
):
    try:
        query = db.query(FCDispatch).filter(FCDispatch.company_id == company_id)
        print(f"[COMPANY FILTER] FCDispatch, {company_id}")
        
        if dispatch_type:
            query = query.filter(FCDispatch.dispatch_type == dispatch_type)
            
        if source_warehouse_id:
            query = query.filter(FCDispatch.source_warehouse_id == source_warehouse_id)
            
        dispatches = query.order_by(FCDispatch.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for d in dispatches:
            result.append({
                "id": d.id,
                "dispatch_number": d.dispatch_number,
                "dispatch_type": d.dispatch_type,
                "dispatch_status": d.dispatch_status,
                "source_warehouse": d.source_warehouse.name if d.source_warehouse else "Unknown",
                "source_warehouse_id": d.source_warehouse_id,
                "warehouse": d.warehouse.name if d.warehouse else "Unknown",
                "hub_code": d.warehouse.hub.hub_code if d.warehouse and d.warehouse.hub else "Unknown",
                "invoice_number": d.invoice.invoice_number if d.invoice else None,
                "challan_number": d.delivery_challan.challan_number if d.delivery_challan else None,
                "created_at": d.created_at.isoformat()
            })
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/inventory")
def get_dispatch_inventory(
    source_warehouse_id: int = Query(..., description="ID of the source warehouse"),
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    """Get available inventory for the selected source warehouse"""
    
    try:
        source_warehouse = db.query(Warehouse).filter(
            Warehouse.id == source_warehouse_id,
            Warehouse.company_id == company_id
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
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/recommendations")
def get_45_day_recommendations(
    current_user: User = Depends(get_current_user)
):
    try:
        """Get the 45-day return recommendations computed dynamically (or from cache in future)"""
        recs = generate_45_day_return_recommendations()
        return recs or []
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")
