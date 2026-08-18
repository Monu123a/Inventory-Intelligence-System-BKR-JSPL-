from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
import logging
from datetime import datetime

from app.models.db import get_db
from app.models.schema import User
from app.api.dependencies import get_current_company_id, require_admin
from app.api.routers.auth import verify_admin_action_password
from app.services.warehouse_service import WarehouseService
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)

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
    admin_password: Optional[str] = Field(default=None, exclude=True)

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
def create_warehouse(warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    verify_admin_action_password(warehouse.admin_password, admin_user)
    try:
        result = WarehouseService.create(db, company_id, warehouse.model_dump())
        db.commit()
        logger.info({
            "action": "CREATE_WAREHOUSE",
            "user_id": admin_user.id,
            "company_id": company_id,
            "warehouse_code": warehouse.code,
            "timestamp": datetime.utcnow().isoformat()
        })
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(warehouse_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh

@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, warehouse: WarehouseBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    verify_admin_action_password(warehouse.admin_password, admin_user)
    try:
        result = WarehouseService.update(db, warehouse_id, company_id, warehouse.model_dump(exclude_unset=True))
        db.commit()
        logger.info({
            "action": "UPDATE_WAREHOUSE",
            "user_id": admin_user.id,
            "company_id": company_id,
            "warehouse_id": warehouse_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return result
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(f"Warehouse update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while updating the warehouse.")

class DeleteWarehouseRequest(BaseModel):
    admin_password: Optional[str] = Field(default=None)

@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, payload: DeleteWarehouseRequest, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    verify_admin_action_password(payload.admin_password, admin_user)
    try:
        WarehouseService.delete(db, warehouse_id, company_id)
        db.commit()
        logger.info({
            "action": "DELETE_WAREHOUSE",
            "user_id": admin_user.id,
            "company_id": company_id,
            "warehouse_id": warehouse_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"detail": "Warehouse deleted successfully"}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{warehouse_id}/users", response_model=List[WarehouseUserResponse])
def get_warehouse_users(warehouse_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseService.get_warehouse_users(db, warehouse_id)

@router.post("/{warehouse_id}/users", response_model=WarehouseUserResponse)
def assign_warehouse_user(warehouse_id: int, data: WarehouseUserBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), admin_user = Depends(require_admin)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    result = WarehouseService.assign_warehouse_user(db, warehouse_id, data.user_id, data.permission)
    
    AuditLogService.log(
        db,
        company_id=company_id,
        entity_type="Warehouse",
        entity_id=warehouse_id,
        event_type="WAREHOUSE_USER_ASSIGNED",
        message=f"User {data.user_id} assigned to warehouse {warehouse_id}"
    )
    
    db.commit()
    return result

@router.delete("/{warehouse_id}/users/{user_id}")
def remove_warehouse_user(warehouse_id: int, user_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), admin_user = Depends(require_admin)):
    wh = WarehouseService.get_by_id(db, warehouse_id, company_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    success = WarehouseService.remove_warehouse_user(db, warehouse_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Warehouse user assignment not found")
        
    AuditLogService.log(
        db,
        company_id=company_id,
        entity_type="Warehouse",
        entity_id=warehouse_id,
        event_type="WAREHOUSE_USER_REMOVED",
        message=f"User {user_id} removed from warehouse {warehouse_id}"
    )
        
    db.commit()
    return {"detail": "User removed from warehouse successfully"}
