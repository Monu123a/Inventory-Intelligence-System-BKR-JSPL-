from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

from app.services.document_number_service import DocumentNumberService
from app.models.schema import DocumentTypeEnum


def _get_fiscal_year_string(d: date) -> str:
    """
    Fiscal year assumed: Apr 1 -> Mar 31.
    Example: 2026-07-31 => 26-27
    """
    start_year = d.year if d.month >= 4 else d.year - 1
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"


class InvoiceNumberService:
    @staticmethod
    def generate_next(db: Session, *, company_id: int, company_code: str, on_date: date | None = None) -> str:
        on_date = on_date or date.today()
        fy = _get_fiscal_year_string(on_date)

        return DocumentNumberService.generate_number(
            db=db,
            company_id=company_id,
            document_type=DocumentTypeEnum.SALE,
            fiscal_year=fy,
            prefix_override=company_code
        )
