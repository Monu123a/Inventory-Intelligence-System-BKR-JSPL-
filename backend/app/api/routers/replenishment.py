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
