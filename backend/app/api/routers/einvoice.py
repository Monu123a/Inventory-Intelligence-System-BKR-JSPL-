from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.schema import Sale, CompanySettings, User
from app.api.dependencies import get_current_company_id, get_current_user
from app.services.einvoice.einvoice_service import EInvoiceService

router = APIRouter(prefix="/einvoice", tags=["E-Invoice"])

class CancelIRNRequest(BaseModel):
    cancel_reason: str = "1" # 1: Duplicate, 2: Data entry mistake, 3: Order cancelled, 4: Others
    remarks: str = "Cancelled by user"

class EInvoiceSettingsUpdate(BaseModel):
    einvoice_enabled: bool = False
    einvoice_provider: str = "CLEARTAX"
    auth_token: Optional[str] = None
    gstin: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    environment: str = "sandbox" # sandbox | production
    auto_generate_on_pos: bool = False

@router.get("/settings")
def get_einvoice_settings(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        return {
            "einvoice_enabled": False,
            "einvoice_provider": "CLEARTAX",
            "environment": "sandbox",
            "gstin": "",
            "auth_token": "",
            "auto_generate_on_pos": False
        }
    config = settings.einvoice_config or {}
    return {
        "einvoice_enabled": bool(settings.einvoice_enabled),
        "einvoice_provider": settings.einvoice_provider or "CLEARTAX",
        "environment": config.get("environment", "sandbox"),
        "gstin": config.get("gstin") or settings.gstin or "",
        "auth_token": config.get("auth_token", ""),
        "client_id": config.get("client_id", ""),
        "client_secret": config.get("client_secret", ""),
        "auto_generate_on_pos": config.get("auto_generate_on_pos", False)
    }

@router.put("/settings")
def update_einvoice_settings(
    payload: EInvoiceSettingsUpdate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        settings = CompanySettings(company_id=company_id)
        db.add(settings)

    settings.einvoice_enabled = payload.einvoice_enabled
    settings.einvoice_provider = payload.einvoice_provider
    settings.einvoice_config = {
        "auth_token": payload.auth_token or "",
        "gstin": payload.gstin or settings.gstin or "",
        "client_id": payload.client_id or "",
        "client_secret": payload.client_secret or "",
        "environment": payload.environment or "sandbox",
        "auto_generate_on_pos": payload.auto_generate_on_pos
    }
    db.commit()
    db.refresh(settings)
    return {"message": "E-Invoice settings updated successfully"}

@router.post("/generate/{sale_id}")
def generate_irn(
    sale_id: int,
    force_retry: bool = Query(False),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found.")

    try:
        result = EInvoiceService.generate_irn_for_sale(sale_id=sale.id, db=db, force_retry=force_retry)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cancel/{sale_id}")
def cancel_irn(
    sale_id: int,
    payload: CancelIRNRequest,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found.")

    try:
        result = EInvoiceService.cancel_irn_for_sale(
            sale_id=sale.id,
            cancel_reason=payload.cancel_reason,
            remarks=payload.remarks,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/{sale_id}")
def get_einvoice_status(
    sale_id: int,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found.")

    return {
        "sale_id": sale.id,
        "invoice_number": sale.invoice_number or sale.bill_number,
        "einvoice_status": sale.einvoice_status or "NOT_GENERATED",
        "einvoice_irn": sale.einvoice_irn,
        "einvoice_ack_no": sale.einvoice_ack_no,
        "einvoice_ack_date": sale.einvoice_ack_date.isoformat() if sale.einvoice_ack_date else None,
        "einvoice_qr_code_data": sale.einvoice_qr_code_data,
        "einvoice_error_message": sale.einvoice_error_message,
        "einvoice_canceled_at": sale.einvoice_canceled_at.isoformat() if sale.einvoice_canceled_at else None,
        "is_b2b": bool(sale.customer_gstin and len(sale.customer_gstin.strip()) >= 15)
    }
