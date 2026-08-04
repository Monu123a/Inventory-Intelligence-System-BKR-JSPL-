from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.auth.dependencies import get_current_user
from app.services.damage_claim_service import DamageClaimService, CreateDamageClaimRequest
from app.models.schema import User, DamageClaim
from pydantic import BaseModel

router = APIRouter(prefix="/damage-claims", tags=["Damage Claims"])

class UpdateClaimStatusRequest(BaseModel):
    status: str

@router.post("/")
def create_damage_claim(
    request: CreateDamageClaimRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new damage claim (locks inventory)"""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
        
    claim = DamageClaimService.create_claim(db, company_id, request, current_user.id)
    return {"message": "Claim created and stock reserved", "claim_number": claim.claim_number}

@router.patch("/{claim_id}/status")
def update_damage_claim_status(
    claim_id: int,
    request: UpdateClaimStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a damage claim"""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
        
    claim = DamageClaimService.update_claim_status(db, company_id, claim_id, request.status, current_user.id)
    return {"message": f"Claim status updated to {claim.claim_status}", "claim_number": claim.claim_number}

@router.get("/")
def get_damage_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    company_id = current_user.company_id
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
