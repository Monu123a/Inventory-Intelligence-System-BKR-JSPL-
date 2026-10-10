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
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    bank_details: Optional[str] = None
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


class VendorCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    bank_details: Optional[str] = None
    payable_balance: Optional[float] = 0.0

@router.post("/", response_model=VendorResponse)
def create_vendor(
    vendor: VendorCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    new_vendor = Vendor(
        company_id=company_id,
        name=vendor.name,
        contact=vendor.contact,
        phone=vendor.phone,
        gst_number=vendor.gst_number,
        address=vendor.address,
        bank_details=vendor.bank_details,
        payable_balance=vendor.payable_balance or 0.0
    )
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    return new_vendor

@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int,
    vendor: VendorCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    db_vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.company_id == company_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    db_vendor.name = vendor.name
    db_vendor.contact = vendor.contact
    db_vendor.phone = vendor.phone
    db_vendor.gst_number = vendor.gst_number
    db_vendor.address = vendor.address
    db_vendor.bank_details = vendor.bank_details
    if vendor.payable_balance is not None:
        db_vendor.payable_balance = vendor.payable_balance
        
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

from app.models.schema import Purchase
from sqlalchemy import desc

@router.get("/{vendor_id}/history")
def get_vendor_history(
    vendor_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    db_vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.company_id == company_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    purchases = db.query(Purchase).filter(Purchase.vendor_name == db_vendor.name, Purchase.company_id == company_id).order_by(desc(Purchase.date)).all()
    
    return {
        "vendor": {
            "id": db_vendor.id,
            "name": db_vendor.name,
            "contact": db_vendor.contact,
            "payable_balance": db_vendor.payable_balance
        },
        "purchases": [
            {
                "id": p.id,
                "invoice_number": p.invoice_number,
                "date": p.date.isoformat() if p.date else None,
                "total_amount": p.total_amount,
                "status": p.status
            }
            for p in purchases
        ]
    }
