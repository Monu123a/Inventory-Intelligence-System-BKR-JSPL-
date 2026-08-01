import re
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
        
        # Get all transfers with this prefix to find the max sequence
        matching_transfers = (
            db.query(StockTransfer)
            .filter(StockTransfer.from_company_id == company_id)
            .filter(StockTransfer.transfer_number.startswith(prefix))
            .all()
        )
        
        seq = 1
        for t in matching_transfers:
            # Extract the sequence number from the last segment, handling any suffixes
            last_segment = t.transfer_number.split('/')[-1]
            # Extract only the leading digits (handles "0001", "0001-BO", etc.)
            match = re.match(r'^(\d+)', last_segment)
            if match:
                num = int(match.group(1))
                seq = max(seq, num + 1)
                
        return f"{prefix}{seq:04d}"
