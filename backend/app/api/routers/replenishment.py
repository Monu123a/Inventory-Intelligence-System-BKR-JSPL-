from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.models.schema import User
from app.services.replenishment_service import ReplenishmentService

router = APIRouter(prefix="/replenishment", tags=["Replenishment"])

@router.post("/analyze/{company_id}")
def analyze_inventory(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        run = ReplenishmentService.analyze_inventory(db, company_id)
        return {"status": "success", "run_id": run.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verify-sync/{company_id}")
def verify_amazon_sync(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        is_synced = ReplenishmentService.verify_amazon_sync(db, company_id)
        return {"status": "success", "synced": is_synced}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from app.models.schema import Inventory, Product
from app.api.dependencies import get_current_company_id

from sqlalchemy import func

@router.get("/recommendations")
def get_recommendations(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    # Group inventory by product_id across all warehouses
    results = db.query(
        Inventory.product_id,
        func.sum(Inventory.available_qty).label("total_qty")
    ).filter(
        Inventory.company_id == company_id,
        Inventory.product_id.in_([1, 2, 3, 4, 5]) # Temporarily limit to a few test products to avoid massive lists
    ).group_by(
        Inventory.product_id
    ).all()

    recommendations = []
    for product_id, total_qty in results:
        total_qty = total_qty or 0
        if total_qty < 10:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                recommendations.append({
                    "id": product.id,
                    "sku": product.sku,
                    "product": product.name,
                    "requiredQty": max(50 - total_qty, 10),
                    "currentStock": total_qty
                })
    return recommendations

