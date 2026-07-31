from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session

from app.models.schema import InvoiceSequence


@dataclass(frozen=True)
class InvoiceNumberParts:
    company_code: str
    fiscal_year: str  # "26-27"
    sequence_no: int

    def format(self) -> str:
        return f"{self.company_code}/{self.fiscal_year}/{self.sequence_no:03d}"


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

        seq = (
            db.query(InvoiceSequence)
            .filter(InvoiceSequence.company_id == company_id, InvoiceSequence.fiscal_year == fy)
            .with_for_update()
            .first()
        )
        if not seq:
            seq = InvoiceSequence(company_id=company_id, fiscal_year=fy, last_number=0)
            db.add(seq)
            db.flush()

        seq.last_number = (seq.last_number or 0) + 1
        db.flush()

        parts = InvoiceNumberParts(company_code=company_code, fiscal_year=fy, sequence_no=seq.last_number)
        return parts.format()

