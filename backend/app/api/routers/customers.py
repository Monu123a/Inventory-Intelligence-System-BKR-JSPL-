from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.models.db import get_db
from app.models.schema import User, Customer
from app.api.deps import get_current_user, get_current_company_id

router = APIRouter(tags=["Customers"])

class CustomerCreate(BaseModel):
    name: str
    mobile: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    place_of_supply: Optional[str] = None

class CustomerResponse(CustomerCreate):
    id: int

@router.get("/", response_model=List[CustomerResponse])
def get_customers(
    search: Optional[str] = None,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(Customer).filter(Customer.company_id == company_id)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Customer.name.ilike(search_term)) | 
            (Customer.mobile.ilike(search_term)) |
            (Customer.phone.ilike(search_term))
        )
    return query.all()

@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Try to find existing first
    if customer.mobile:
        existing = db.query(Customer).filter_by(company_id=company_id, mobile=customer.mobile).first()
        if existing:
            # Update existing with new details if they are provided
            for k, v in customer.dict(exclude_unset=True).items():
                if v is not None:
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
            
    new_customer = Customer(
        company_id=company_id,
        **customer.dict()
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

