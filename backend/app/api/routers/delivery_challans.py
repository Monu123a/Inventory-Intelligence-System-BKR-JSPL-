from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user
from app.services.delivery_challan_service import DeliveryChallanService
from app.models.schema import DeliveryChallan, User

router = APIRouter(prefix="/delivery-challans", tags=["Delivery Challans"])

class DeliveryChallanItemCreate(BaseModel):
    product_id: Optional[int] = None
    sku_snapshot: Optional[str] = None
    product_name_snapshot: Optional[str] = None
    hsn_snapshot: Optional[str] = None
    unit_snapshot: Optional[str] = None
    quantity: int = Field(..., gt=0)
    unit_price: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total_price: float = 0.0

class DeliveryChallanCreate(BaseModel):
    challan_number: Optional[str] = None
    sale_id: Optional[int] = None
    seller_snapshot: Optional[dict] = None
    buyer_snapshot: Optional[dict] = None
    shipping_snapshot: Optional[dict] = None
    vehicle_number: Optional[str] = None
    transport_mode: Optional[str] = None
    eway_bill: Optional[str] = None
    remarks: Optional[str] = None
    items: List[DeliveryChallanItemCreate] = []

class DeliveryChallanItemResponse(DeliveryChallanItemCreate):
    id: int
    challan_id: int
    model_config = ConfigDict(from_attributes=True)

from datetime import datetime

class DeliveryChallanResponse(DeliveryChallanCreate):
    id: int
    company_id: int
    status: str
    print_count: int
    challan_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    last_printed_at: Optional[datetime] = None
    items: List[DeliveryChallanItemResponse]
    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=DeliveryChallanResponse)
def create_challan(
    data: DeliveryChallanCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    challan = DeliveryChallanService.create_challan(db, company_id, data.model_dump(), user.id)
    db.commit()
    db.refresh(challan)
    return challan

@router.post("/{challan_id}/print", response_model=DeliveryChallanResponse)
def print_challan(
    challan_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        challan = DeliveryChallanService.print_challan(db, company_id, challan_id)
        db.commit()
        db.refresh(challan)
        return challan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{challan_id}/cancel", response_model=DeliveryChallanResponse)
def cancel_challan(
    challan_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        challan = DeliveryChallanService.cancel_challan(db, company_id, challan_id)
        db.commit()
        db.refresh(challan)
        return challan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[DeliveryChallanResponse])
def list_challans(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    return db.query(DeliveryChallan).filter(DeliveryChallan.company_id == company_id).all()

@router.get("/{challan_id}", response_model=DeliveryChallanResponse)
def get_challan(
    challan_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    challan = db.query(DeliveryChallan).filter(
        DeliveryChallan.id == challan_id,
        DeliveryChallan.company_id == company_id
    ).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    return challan
