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
    query = db.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.min_stock_level,
        Product.reorder_level,
        func.coalesce(func.sum(Inventory.available_qty), 0).label("total_qty")
    ).join(
        Inventory, (Product.id == Inventory.product_id) & (Inventory.company_id == Product.company_id)
    ).filter(
        Product.company_id == company_id
    )

    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    elif state_hub_id:
        query = query.join(Warehouse, Inventory.warehouse_id == Warehouse.id).filter(Warehouse.hub_id == state_hub_id)

    results = query.group_by(
        Product.id,
        Product.sku,
        Product.name,
        Product.min_stock_level,
        Product.reorder_level
    ).all()

    recommendations = []
    for prod_id, sku, name, min_stock_val, reorder_lvl, total_qty in results:
        total_qty = total_qty or 0
        min_stock = min_stock_val if (min_stock_val and min_stock_val > 0) else 0
        reorder_level = reorder_lvl if (reorder_lvl and reorder_lvl > 0) else 0
        
        is_below_min = (min_stock > 0 and total_qty < min_stock)
        is_out_of_stock = (total_qty <= 0)

        if is_below_min or is_out_of_stock:
            if reorder_level > 0:
                required = max(reorder_level - total_qty, 1)
            elif min_stock > 0:
                required = max(min_stock - total_qty, 1)
            else:
                required = max(10 - total_qty, 10)

            recommendations.append({
                "id": prod_id,
                "sku": sku,
                "product": name,
                "requiredQty": required,
                "currentStock": total_qty
            })

    # Sort most urgent deficits and zero stock to the top
    recommendations.sort(key=lambda x: (x["currentStock"], x["sku"]))
    return recommendations

