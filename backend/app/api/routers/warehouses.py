from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.db import get_db
from app.api.dependencies import get_current_company_id
from app.services.warehouse_service import WarehouseService

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])

from app.models.schema import WarehouseType, WarehouseStatus

class ExternalMappingBase(BaseModel):
    marketplace: str
    external_code: str

class ExternalMappingResponse(ExternalMappingBase):
    id: int
    warehouse_id: int
    model_config = ConfigDict(from_attributes=True)

class WarehouseBase(BaseModel):
    name: str
    code: str
    hub_id: Optional[int] = None
    warehouse_type: WarehouseType = WarehouseType.FULFILLMENT_CENTER
    status: WarehouseStatus = WarehouseStatus.ACTIVE
    address: Optional[str] = None
    contact_person: Optional[str] = None
    manager: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    external_mappings: Optional[List[ExternalMappingBase]] = []

class WarehouseResponse(WarehouseBase):
    id: int
    company_id: int
    external_mappings: List[ExternalMappingResponse] = []
    model_config = ConfigDict(from_attributes=True)

class WarehouseUserBase(BaseModel):
    user_id: int
    permission: str = "VIEW"

class WarehouseUserResponse(WarehouseUserBase):
    id: int
    warehouse_id: int
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[WarehouseResponse])
def get_warehouses(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    return WarehouseService.get_all(db, company_id)

@router.post("/", response_model=WarehouseResponse)
def create_warehouse(warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        return WarehouseService.create(db, company_id, warehouse.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(warehouse_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh

@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        return WarehouseService.update(db, warehouse_id, company_id, warehouse.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        WarehouseService.delete(db, warehouse_id, company_id)
        return {"detail": "Warehouse deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{warehouse_id}/users", response_model=List[WarehouseUserResponse])
def get_warehouse_users(warehouse_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseService.get_warehouse_users(db, warehouse_id)

@router.post("/{warehouse_id}/users", response_model=WarehouseUserResponse)
def assign_warehouse_user(warehouse_id: int, data: WarehouseUserBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseService.assign_warehouse_user(db, warehouse_id, data.user_id, data.permission)

@router.delete("/{warehouse_id}/users/{user_id}")
def remove_warehouse_user(warehouse_id: int, user_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    success = WarehouseService.remove_warehouse_user(db, warehouse_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Warehouse user assignment not found")
    return {"detail": "User removed from warehouse successfully"}
