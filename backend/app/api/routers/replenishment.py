from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.schema import User, Inventory, Product
from app.api.dependencies import get_current_user, get_db, get_current_company_id
from app.services.replenishment_service import ReplenishmentService

router = APIRouter(prefix="/replenishment", tags=["Replenishment"])

@router.post("/analyze")
def analyze_inventory(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        run = ReplenishmentService.analyze_inventory(db, company_id)
        return {"status": "success", "run_id": run.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verify-sync")
def verify_amazon_sync(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        is_synced = ReplenishmentService.verify_amazon_sync(db, company_id)
        return {"status": "success", "synced": is_synced}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from sqlalchemy import func

@router.get("/recommendations")
def get_recommendations(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    # Group inventory by product_id across all warehouses
    results = db.query(
        Inventory.product_id,
        func.sum(Inventory.available_qty).label("total_qty")
    ).filter(
        Inventory.company_id == company_id
    ).group_by(
        Inventory.product_id
    ).all()

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

