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
    sku: str
    name: str
    category: Optional[str] = None
    quantity: int
    reserved_qty: int
    available_qty: int
    last_updated: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[WarehouseInventoryResponse])
def get_warehouse_inventory(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    sku: Optional[str] = Query(None, description="Filter by product SKU"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    items = WarehouseInventoryViewService.get_inventory_view(db, company_id, warehouse_id, category, sku)
    
    response_items = []
    for item in items:
        # The query joins Product, so item.product is loaded
        response_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "warehouse_id": item.warehouse_id,
            "sku": item.product.sku if item.product else "UNKNOWN",
            "name": item.product.name if item.product else "Unknown Product",
            "category": item.product.category if item.product else "Uncategorized",
            "hsn": item.product.hsn if item.product else None,
            "quantity": item.current_qty,
            "reserved_qty": item.reserved_qty,
            "available_qty": item.available_qty,
            "last_updated": item.last_updated
        })
        
    return response_items
