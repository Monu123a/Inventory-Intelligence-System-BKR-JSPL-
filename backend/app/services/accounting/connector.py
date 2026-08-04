from abc import ABC, abstractmethod
from typing import List
from sqlalchemy.orm import Session
from app.services.accounting.dtos import InvoiceDTO, AccountingExportResult

class AccountingConnector(ABC):
    """
    Base class for all accounting integrations (Tally, Zoho, Busy, etc.).
    """
    
    def __init__(self, db: Session, company_id: int):
        self.db = db
        self.company_id = company_id
        
    @abstractmethod
    def generate_invoice_export(self, invoices: List[InvoiceDTO]) -> AccountingExportResult:
        """
        Takes a list of InvoiceDTOs (to support batching natively) and returns
        the generated payload (e.g., XML string) and status.
        """
        pass

    @abstractmethod
    def generate_master_export(self, master_type: str, entities: List[dict]) -> AccountingExportResult:
        """
        Generates master sync payload for Customers, Products, etc.
        """
        pass
