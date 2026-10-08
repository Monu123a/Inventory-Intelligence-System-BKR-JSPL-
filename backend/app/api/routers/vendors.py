from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.models.db import get_db
from app.models.schema import User, Vendor
from app.api.dependencies import get_current_user, get_current_company_id

router = APIRouter(tags=["Vendors"])

class VendorResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    payable_balance: float

    class Config:
        orm_mode = True

@router.get("/", response_model=List[VendorResponse])
def get_vendors(
    search: Optional[str] = None,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(Vendor).filter(Vendor.company_id == company_id)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(Vendor.name.ilike(search_term))
    return query.all()
