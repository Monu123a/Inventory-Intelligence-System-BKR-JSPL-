from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.models.schema import User
from app.services.service_reminder_service import ServiceReminderService
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/service-reminders", tags=["Service Reminders"])

class ServiceReminderResponse(BaseModel):
    id: int
    sale_id: int
    product_id: int
    customer_name_snapshot: Optional[str] = None
    customer_mobile_snapshot: Optional[str] = None
    sale_date: datetime
    reminder_date: datetime
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[ServiceReminderResponse])
def get_reminders(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    from app.models.schema import ServiceReminder
    return db.query(ServiceReminder).filter(ServiceReminder.company_id == company_id).order_by(ServiceReminder.reminder_date.asc()).all()

@router.post("/{id}/status", response_model=ServiceReminderResponse)
def update_reminder_status(
    id: int,
    status: str,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    try:
        reminder = ServiceReminderService.update_status(db, company_id, id, status)
        db.commit()
        db.refresh(reminder)
        AuditLogService.log(
            db, 
            company_id=company_id, 
            entity_type="ServiceReminder", 
            entity_id=reminder.id, 
            event_type="REMINDER_STATUS_UPDATED", 
            message=f"Reminder status updated to {status}"
        )
        return reminder
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
