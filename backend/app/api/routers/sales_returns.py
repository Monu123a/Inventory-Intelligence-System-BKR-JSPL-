from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user
from app.services.sales_return_service import SalesReturnService
from app.models.schema import SalesReturn, User

router = APIRouter(prefix="/sales-returns", tags=["Sales Returns"])

class SalesReturnItemCreate(BaseModel):
    sale_item_id: Optional[int] = None
    product_id: Optional[int] = None
    sku_snapshot: Optional[str] = None
    product_name_snapshot: Optional[str] = None
    returned_quantity: int
    return_reason: Optional[str] = None
    unit_price: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total_price: float = 0.0

class SalesReturnCreate(BaseModel):
    sale_id: Optional[int] = None
    return_number: Optional[str] = None
    return_type: str = "OFFLINE"
    customer_name: Optional[str] = None
    total_taxable_amount: float = 0.0
    total_tax: float = 0.0
    grand_total: float = 0.0
    items: List[SalesReturnItemCreate]

class SalesReturnItemResponse(SalesReturnItemCreate):
    id: int
    return_id: int
    hsn_snapshot: Optional[str] = None
    unit_snapshot: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

from datetime import datetime

class SalesReturnResponse(SalesReturnCreate):
    id: int
    company_id: int
    status: str
    return_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    items: List[SalesReturnItemResponse]
    model_config = ConfigDict(from_attributes=True)

@router.post("/draft", response_model=SalesReturnResponse)
def create_draft_return(
    data: SalesReturnCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        rtn = SalesReturnService.create_draft(db, company_id, data.model_dump(), user.id)
        db.commit()
        db.refresh(rtn)
        return rtn
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{return_id}/complete", response_model=SalesReturnResponse)
def complete_return(
    return_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        rtn = SalesReturnService.complete_return(db, company_id, return_id, user.id)
        db.commit()
        db.refresh(rtn)
        return rtn
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{return_id}/cancel", response_model=SalesReturnResponse)
def cancel_return(
    return_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        rtn = SalesReturnService.cancel_return(db, company_id, return_id)
        db.commit()
        db.refresh(rtn)
        return rtn
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[SalesReturnResponse])
def list_returns(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(SalesReturn).filter(SalesReturn.company_id == company_id).all()
