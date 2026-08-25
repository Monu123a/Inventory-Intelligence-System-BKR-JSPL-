from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.db import get_db
from app.models.schema import Company, CompanyUser, User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/companies", tags=["Companies"])

class CompanyResponse(BaseModel):
    id: int
    name: str
    code: str
    status: str
    legal_name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[CompanyResponse])
def get_companies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.schema import CompanySettings
    
    companies = db.query(Company).join(CompanyUser).filter(
        CompanyUser.user_id == current_user.id,
        Company.status == "Active"
    ).all()
    
    result = []
    for comp in companies:
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == comp.id).first()
        result.append({
            "id": comp.id,
            "name": comp.name,
            "code": comp.code,
            "status": comp.status,
            "legal_name": settings.legal_name if settings else comp.name,
            "gstin": settings.gstin if settings else None,
            "address": settings.address if settings else None,
            "state": settings.state if settings else None,
            "state_code": settings.state_code if settings else None
        })
        
    return result
