from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.schema import CompanySettings
from app.api.dependencies import get_current_company_id, require_admin


router = APIRouter(prefix="/settings", tags=["Company Settings"])


class CompanySettingsResponse(BaseModel):
    tally_enabled: bool = False
    tally_endpoint_url: str | None = None
    tally_payload_format: str = "XML"

    legal_name: str | None = None
    gstin: str | None = None
    address: str | None = None
    state: str | None = None
    state_code: str | None = None
    email: str | None = None
    phone: str | None = None
    logo_url: str | None = None
    bank_details: dict | None = None

    declaration: str | None = None
    terms_of_delivery_default: str | None = None
    smtp_settings: dict | None = None


class CompanySettingsUpdate(BaseModel):
    tally_enabled: bool | None = None
    tally_endpoint_url: str | None = None
    tally_payload_format: str | None = None

    legal_name: str | None = None
    gstin: str | None = None
    address: str | None = None
    state: str | None = None
    state_code: str | None = None
    email: str | None = None
    phone: str | None = None
    logo_url: str | None = None
    bank_details: dict | None = None

    declaration: str | None = None
    terms_of_delivery_default: str | None = None
    smtp_settings: dict | None = None


@router.get("/", response_model=CompanySettingsResponse)
def get_settings(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        return CompanySettingsResponse()
    return CompanySettingsResponse(
        tally_enabled=bool(settings.tally_enabled),
        tally_endpoint_url=settings.tally_endpoint_url,
        tally_payload_format=settings.tally_payload_format or "XML",
        legal_name=settings.legal_name,
        gstin=settings.gstin,
        address=settings.address,
        state=settings.state,
        state_code=settings.state_code,
        email=settings.email,
        phone=settings.phone,
        logo_url=settings.logo_url,
        bank_details=settings.bank_details,
        declaration=settings.declaration,
        terms_of_delivery_default=settings.terms_of_delivery_default,
        smtp_settings=settings.smtp_settings,
    )


@router.put("/", response_model=CompanySettingsResponse)
def update_company_settings(
    payload: CompanySettingsUpdate,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings:
        settings = CompanySettings(company_id=company_id)
        db.add(settings)
        db.flush()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return get_settings(company_id=company_id, db=db)
