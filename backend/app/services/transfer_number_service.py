from datetime import date
from sqlalchemy.orm import Session
from app.models.schema import StockTransfer, Company

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

        prefix = f"TRF/{company_code}/{fy}/"
        
        last_transfer = (
            db.query(StockTransfer)
            .filter(StockTransfer.from_company_id == company_id)
            .filter(StockTransfer.transfer_number.startswith(prefix))
            .order_by(StockTransfer.id.desc())
            .first()
        )
        
        seq = 1
        if last_transfer:
            try:
                seq = int(last_transfer.transfer_number.split('/')[-1]) + 1
            except ValueError:
                seq = 1
                
        return f"{prefix}{seq:04d}"
