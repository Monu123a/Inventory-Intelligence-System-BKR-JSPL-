from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.db import get_db
from app.api.dependencies import get_current_company_id, get_current_user
from app.models.schema import User

from app.schemas.service import (
    JobCardCreate, JobCardDirectCreate, JobCardResponse, JobCardUpdateStatus,
    ServiceInvoiceCreate, ServiceInvoiceResponse
)
from app.services.job_card_service import JobCardService
from app.services.service_invoice_service import ServiceInvoiceService

router = APIRouter(prefix="/bkr-services", tags=["BKR Service Module"])

@router.post("/job-cards", response_model=JobCardResponse)
def create_job_card(
    job_card_in: JobCardDirectCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    service = JobCardService(db)
    try:
        return service.create_direct_job_card(company_id, job_card_in, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/job-cards", response_model=List[JobCardResponse])
def get_job_cards(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    service = JobCardService(db)
    return service.get_job_cards(company_id)

@router.get("/job-cards/{job_card_id}", response_model=JobCardResponse)
def get_job_card(
    job_card_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    service = JobCardService(db)
    return service.get_job_card(company_id, job_card_id)

@router.patch("/job-cards/{job_card_id}/status", response_model=JobCardResponse)
def update_job_card_status(
    job_card_id: int,
    status_data: JobCardUpdateStatus,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    service = JobCardService(db)
    try:
        return service.update_status(company_id, job_card_id, status_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/invoices", response_model=ServiceInvoiceResponse)
def generate_service_invoice(
    invoice_in: ServiceInvoiceCreate,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    service = ServiceInvoiceService(db)
    try:
        return service.generate_invoice(company_id, invoice_in, user_id=current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/invoices", response_model=List[ServiceInvoiceResponse])
def get_service_invoices(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    service = ServiceInvoiceService(db)
    return service.get_invoices(company_id)

@router.get("/invoices/{invoice_id}", response_model=ServiceInvoiceResponse)
def get_service_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    service = ServiceInvoiceService(db)
    return service.get_invoice(company_id, invoice_id)
