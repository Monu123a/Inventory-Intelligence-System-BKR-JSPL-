from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.services.fc_return_service import FCReturnService, FCReturnRequest
from app.models.schema import User, FCReturn

router = APIRouter(prefix="/fc-returns", tags=["FC Returns"])

@router.post("/")
def create_fc_return(
    request: FCReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id)
):
    """Create a new FC return (partial or full) against a dispatch"""
        
    try:
        fc_return = FCReturnService.process_return(db, company_id, request, current_user.id)
        db.commit()
        return {"message": "Return processed successfully", "return_number": fc_return.return_number}
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
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/")
def get_fc_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id),
    skip: int = 0,
    limit: int = 100
):
    try:
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
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")
