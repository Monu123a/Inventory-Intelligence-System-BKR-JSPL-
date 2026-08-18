from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user, require_manager
from app.services.damage_claim_service import DamageClaimService, CreateDamageClaimRequest
from app.models.schema import User, DamageClaim
from pydantic import BaseModel
from app.services.metrics_service import log_metric
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/damage-claims", tags=["Damage Claims"])

class UpdateClaimStatusRequest(BaseModel):
    status: str

@router.post("/")
def create_damage_claim(
    request: CreateDamageClaimRequest,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    manager_user: User = Depends(require_manager)
):
    """Create a new damage claim (locks inventory)"""
    try:
        claim = DamageClaimService.create_claim(db, company_id, request, current_user.id)
        db.commit()
        
        logger.info(f"Action: Damage Claim Create | User: {current_user.id} | Company: {company_id} | Status: Success | Claim: {claim.claim_number}")
        log_metric("damage_claim_created", 1, {"company_id": company_id})
        
        return {"message": "Claim created and stock reserved", "claim_number": claim.claim_number}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{claim_id}/status")
def update_damage_claim_status(
    claim_id: int,
    request: UpdateClaimStatusRequest,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    manager_user: User = Depends(require_manager)
):
    """Approve or reject a damage claim"""
        
    try:
        claim = DamageClaimService.update_claim_status(db, company_id, claim_id, request.status, current_user.id)
        db.commit()
        
        logger.info(f"Action: Damage Claim Update | User: {current_user.id} | Company: {company_id} | Status: Success | Claim: {claim.claim_number} | NewStatus: {request.status}")
        log_metric("damage_claim_updated", 1, {"company_id": company_id})
        
        return {"message": f"Claim status updated to {claim.claim_status}", "claim_number": claim.claim_number}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def get_damage_claims(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    claims = db.query(DamageClaim).filter(DamageClaim.company_id == company_id).order_by(DamageClaim.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for c in claims:
        result.append({
            "id": c.id,
            "claim_number": c.claim_number,
            "claim_status": c.claim_status,
            "warehouse": c.warehouse.name if c.warehouse else "Unknown",
            "product_sku": c.product.sku if c.product else "Unknown",
            "quantity": c.quantity,
            "created_at": c.created_at.isoformat(),
        })
    return result
