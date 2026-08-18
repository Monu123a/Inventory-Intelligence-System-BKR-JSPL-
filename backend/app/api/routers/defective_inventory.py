from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.models.db import get_db
from app.models.schema import DefectiveInventory
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/defective-inventory", tags=["Defective Inventory"])

class DefectiveInventoryBase(BaseModel):
    amazon_return_id: int
    product_id: int
    sku_snapshot: str
    product_name_snapshot: Optional[str] = None
    quantity: int
    return_reason: Optional[str] = None
    inspection_notes: Optional[str] = None
    inspection_images: Optional[list] = []
    inspector_id: Optional[int] = None
    inspection_date: Optional[datetime] = None
    status: str

class DefectiveInventoryResponse(DefectiveInventoryBase):
    id: int
    company_id: int
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[DefectiveInventoryResponse])
def get_defective_inventory(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    sku: Optional[str] = None
):
    query = db.query(DefectiveInventory).filter(DefectiveInventory.company_id == company_id)
    
    if status:
        query = query.filter(DefectiveInventory.status == status)
    if sku:
        query = query.filter(DefectiveInventory.sku_snapshot.ilike(f"%{sku}%"))
        
    return query.order_by(DefectiveInventory.inspection_date.desc().nulls_last()).all()
