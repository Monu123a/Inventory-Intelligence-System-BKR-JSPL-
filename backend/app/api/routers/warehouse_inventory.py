from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.models.db import get_db
from app.api.dependencies import get_current_company_id
from app.services.warehouse_inventory_view_service import WarehouseInventoryViewService

router = APIRouter(prefix="/warehouse-inventory", tags=["Warehouse Inventory Views"])

class WarehouseInventoryResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    current_qty: int
    reserved_qty: int
    available_qty: int
    last_updated: Optional[datetime]
    product_sku: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[WarehouseInventoryResponse])
def get_warehouse_inventory(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    sku: Optional[str] = Query(None, description="Filter by product SKU"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    return WarehouseInventoryViewService.get_inventory_view(db, company_id, warehouse_id, category, sku)
