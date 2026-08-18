from datetime import date
from sqlalchemy.orm import Session
from app.models.schema import Company, DocumentTypeEnum
from app.services.document_number_service import DocumentNumberService

def _get_fiscal_year_string(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"

class TransferNumberService:
    @staticmethod
    def generate_next(db: Session, *, company_id: int, on_date: date | None = None) -> str:
        on_date = on_date or date.today()
        fy = _get_fiscal_year_string(on_date)
        
        company = db.query(Company).filter(Company.id == company_id).first()
        company_code = company.code if company else "CMP"
        prefix = f"TRF/{company_code}"

        return DocumentNumberService.generate_number(
            db=db,
            company_id=company_id,
            document_type=DocumentTypeEnum.TRANSFER,
            fiscal_year=fy,
            prefix_override=prefix
        )
