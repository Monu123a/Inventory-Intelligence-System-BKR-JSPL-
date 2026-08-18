from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.models.schema import Inventory, Product
from app.api.dependencies import get_db, get_current_company_id
from app.services.replenishment_service import ReplenishmentService

router = APIRouter(prefix="/replenishment", tags=["Replenishment"])

@router.post("/analyze")
def analyze_inventory(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        run = ReplenishmentService.analyze_inventory(db, company_id)
        db.commit()
        return {"status": "success", "run_id": run.id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verify-sync")
def verify_amazon_sync(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        is_synced = ReplenishmentService.verify_amazon_sync(db, company_id)
        return {"status": "success", "synced": is_synced}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

from sqlalchemy import func
from app.models.schema import Warehouse

@router.get("/recommendations")
def get_recommendations(
    company_id: int = Depends(get_current_company_id), 
    db: Session = Depends(get_db),
    state_hub_id: Optional[int] = None,
    warehouse_id: Optional[int] = None
):
    
    # Group inventory by product_id
    query = db.query(
        Inventory.product_id,
        func.sum(Inventory.available_qty).label("total_qty")
    ).filter(
        Inventory.company_id == company_id
    )

    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    elif state_hub_id:
        query = query.join(Warehouse, Inventory.warehouse_id == Warehouse.id).filter(Warehouse.hub_id == state_hub_id)

    results = query.group_by(Inventory.product_id).all()

    recommendations = []
    for product_id, total_qty in results:
        total_qty = total_qty or 0
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.company_id == company_id
        ).first()
        if not product:
            continue
        
        # Use product-level thresholds, with sensible defaults
        min_stock = product.min_stock_level if product.min_stock_level is not None else 10
        
        if min_stock <= 0:
            continue
            
        reorder_level = product.reorder_level if product.reorder_level is not None else 50
        
        if total_qty < min_stock:
            recommendations.append({
                "id": product.id,
                "sku": product.sku,
                "product": product.name,
                "requiredQty": max(reorder_level - total_qty, 10),
                "currentStock": total_qty
            })
    return recommendations

