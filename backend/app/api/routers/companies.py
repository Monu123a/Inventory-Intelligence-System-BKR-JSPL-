from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
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

    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[CompanyResponse])
def get_companies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    companies = db.query(Company).join(CompanyUser).filter(
        CompanyUser.user_id == current_user.id,
        Company.status == "Active"
    ).all()
    
    return companies
