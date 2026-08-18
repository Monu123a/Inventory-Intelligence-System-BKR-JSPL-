from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.models.schema import User
from app.services.service_record_service import ServiceRecordService
from app.services.audit_log_service import AuditLogService
from app.models.schema import ServiceRecord

router = APIRouter(prefix="/services", tags=["Service Management"])

class ServiceRecordItemCreate(BaseModel):
    product_id: Optional[int] = None
    sku_snapshot: Optional[str] = None
    quantity: int = 1
    serial_number: Optional[str] = None

class ServiceRecordCreate(BaseModel):
    customer_id: Optional[int] = None
    customer_name_snapshot: str
    customer_mobile_snapshot: Optional[str] = None
    customer_email_snapshot: Optional[str] = None
    customer_address_snapshot: Optional[str] = None
    source_type: str = "manual"
    source_invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    sale_type: Optional[str] = None
    marketplace: Optional[str] = None
    service_date: Optional[datetime] = None
    service_type: str
    machine_type: Optional[str] = None
    brand: Optional[str] = None
    power_type: Optional[str] = None
    warranty: bool = False
    service_location: Optional[str] = None
    complaint: Optional[str] = None
    technician_notes: Optional[str] = None
    items: List[ServiceRecordItemCreate] = []

class ServiceRecordItemResponse(BaseModel):
    id: int
    service_record_id: int
    product_id: Optional[int]
    sku_snapshot: Optional[str]
    quantity: int
    serial_number: Optional[str]
    replacement_product_id: Optional[int]
    replacement_quantity: int
    model_config = ConfigDict(from_attributes=True)

class LinkedInvoice(BaseModel):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LinkedJobCard(BaseModel):
    id: int
    job_card_number: str
    status: str
    invoices: List[LinkedInvoice] = []
    model_config = ConfigDict(from_attributes=True)

class ServiceRecordResponse(BaseModel):
    id: int
    service_number: str
    customer_id: Optional[int]
    customer_name_snapshot: str
    customer_mobile_snapshot: Optional[str]
    customer_email_snapshot: Optional[str]
    customer_address_snapshot: Optional[str]
    source_type: str
    source_invoice_id: Optional[str]
    invoice_number: Optional[str]
    sale_type: Optional[str]
    marketplace: Optional[str]
    service_date: datetime
    service_type: str
    machine_type: Optional[str]
    brand: Optional[str]
    power_type: Optional[str]
    warranty: bool
    service_location: Optional[str]
    status: str
    complaint: Optional[str]
    technician_notes: Optional[str]
    labour_charges: float
    spare_charges: float
    tax_amount: float
    grand_total: float
    items: List[ServiceRecordItemResponse]
    job_cards: List[LinkedJobCard] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=ServiceRecordResponse)
def create_service(
    data: ServiceRecordCreate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        record = ServiceRecordService.create_record(db, company_id, data.model_dump(), user.id)
        db.commit()
        db.refresh(record)
        AuditLogService.log(
            db, 
            company_id=company_id, 
            entity_type="ServiceRecord", 
            entity_id=record.id, 
            event_type="SERVICE_CREATED", 
            message=f"Service Record {record.service_number} created", 
            metadata={"service_number": record.service_number}
        )
        return record
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[ServiceRecordResponse])
def get_services(
    status: Optional[str] = None,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    q = db.query(ServiceRecord).filter(ServiceRecord.company_id == company_id)
    if status:
        if status == "active":
            q = q.filter(ServiceRecord.status.in_(["Pending", "In Progress"]))
        elif status == "history":
            q = q.filter(ServiceRecord.status.in_(["Completed", "Cancelled"]))
        else:
            q = q.filter(ServiceRecord.status == status)
    return q.order_by(ServiceRecord.created_at.desc()).all()

@router.get("/{id}", response_model=ServiceRecordResponse)
def get_service(
    id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    record = db.query(ServiceRecord).filter(ServiceRecord.id == id, ServiceRecord.company_id == company_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

@router.post("/{id}/status", response_model=ServiceRecordResponse)
def update_service_status(
    id: int,
    status: str = Body(..., embed=True),
    technician_notes: Optional[str] = Body(None, embed=True),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        record = ServiceRecordService.update_status(db, company_id, id, status, technician_notes)
        db.commit()
        db.refresh(record)
        AuditLogService.log(
            db, 
            company_id=company_id, 
            entity_type="ServiceRecord", 
            entity_id=record.id, 
            event_type="SERVICE_UPDATED", 
            message=f"Status updated to {status}"
        )
        return record
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/items/{item_id}/replacement")
def record_replacement(
    item_id: int,
    replacement_product_id: int,
    quantity: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    try:
        item = ServiceRecordService.record_replacement(db, company_id, item_id, replacement_product_id, quantity)
        db.commit()
        return {"status": "success", "replacement_product_id": item.replacement_product_id}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/bill", response_model=ServiceRecordResponse)
def update_bill(
    id: int,
    labour_charges: float,
    spare_charges: float,
    tax_amount: float,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    try:
        record = ServiceRecordService.update_bill(db, company_id, id, labour_charges, spare_charges, tax_amount)
        db.commit()
        db.refresh(record)
        return record
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
