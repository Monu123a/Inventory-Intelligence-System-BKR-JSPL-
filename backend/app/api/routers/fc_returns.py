from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.api.dependencies import get_current_user
from app.services.fc_return_service import FCReturnService, FCReturnRequest
from app.models.schema import User, FCReturn

router = APIRouter(prefix="/fc-returns", tags=["FC Returns"])

@router.post("/")
def create_fc_return(
    request: FCReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new FC return (partial or full) against a dispatch"""
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
        
    fc_return = FCReturnService.process_return(db, company_id, request, current_user.id)
    return {"message": "Return processed successfully", "return_number": fc_return.return_number}

@router.get("/")
def get_fc_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    company_id = current_user.company_id
    returns = db.query(FCReturn).filter(FCReturn.company_id == company_id).order_by(FCReturn.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for r in returns:
        result.append({
            "id": r.id,
            "return_number": r.return_number,
            "status": r.status,
            "warehouse": r.warehouse.name if r.warehouse else "Unknown",
            "dispatch_number": r.dispatch.dispatch_number if r.dispatch else None,
            "created_at": r.created_at.isoformat(),
        })
    return result
