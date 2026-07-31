from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.db import get_db
from app.models.schema import Warehouse
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])

class WarehouseBase(BaseModel):
    name: str
    code: str
    status: str = "Active"
    address: Optional[str] = None
    contact_person: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

class WarehouseResponse(WarehouseBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[WarehouseResponse])
def get_warehouses(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    return db.query(Warehouse).filter(Warehouse.company_id == company_id).all()

@router.post("/", response_model=WarehouseResponse)
def create_warehouse(warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    existing = db.query(Warehouse).filter(Warehouse.code == warehouse.code, Warehouse.company_id == company_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Warehouse with this code already exists")
    new_wh = Warehouse(**warehouse.model_dump(), company_id=company_id)
    db.add(new_wh)
    db.commit()
    db.refresh(new_wh)
    return new_wh

@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    existing = db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.company_id == company_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    for key, value in warehouse.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)
        
    db.commit()
    db.refresh(existing)
    return existing
