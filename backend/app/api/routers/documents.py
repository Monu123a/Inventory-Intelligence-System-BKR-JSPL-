from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.api.dependencies import get_current_company_id
from app.services.email_service import EmailService
from app.models.schema import Sale

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/invoice/{id}/email")
async def email_invoice(
    id: int,
    to_email: str = Form(...),
    subject: str = Form("Your Invoice"),
    body: str = Form("Please find your invoice attached."),
    file: UploadFile = File(...),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    content = await file.read()
    EmailService.send_email_with_attachment(
        db=db,
        company_id=company_id,
        to_email=to_email,
        subject=subject,
        body=body,
        attachment_filename=file.filename,
        attachment_content=content,
        content_type=file.content_type
    )
    return {"message": "Email sent successfully"}
