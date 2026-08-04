import os
from typing import List, Dict, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services.accounting.connector import AccountingConnector
from app.services.accounting.dtos import InvoiceDTO, AccountingExportResult
from app.models.accounting_schema import AccountingConfiguration, AccountingMapping

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "tally", "v1")

class TallyXMLConnector(AccountingConnector):
    def __init__(self, db: Session, company_id: int):
        super().__init__(db, company_id)
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        self.config = self._load_config()
        self.mappings = self._load_mappings()

    def _load_config(self) -> AccountingConfiguration:
        config = self.db.query(AccountingConfiguration).filter_by(company_id=self.company_id).first()
        if not config:
            config = AccountingConfiguration(company_id=self.company_id, default_sales_ledger="Sales", default_godown="Main Location", round_off_ledger="Round Off")
            self.db.add(config)
            self.db.commit()
        return config
        
    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        mappings = self.db.query(AccountingMapping).filter_by(company_id=self.company_id).all()
        result = {"Ledger": {}, "Product": {}, "Company": {}}
        for m in mappings:
            result[m.mapping_type][m.erp_reference] = m.accounting_name
        return result

    def _resolve_ledger(self, erp_ref: str) -> str:
        return self.mappings["Ledger"].get(erp_ref, erp_ref)

    def _resolve_product(self, erp_ref: str) -> str:
        return self.mappings["Product"].get(erp_ref, erp_ref)
        
    def _resolve_company(self, erp_ref: str) -> str:
        return self.mappings["Company"].get(erp_ref, erp_ref)

    def _render_invoice(self, invoice: InvoiceDTO) -> str:
        template = self.jinja_env.get_template("sales.xml.j2")
        
        # Calculate totals for taxes
        total_cgst = sum(line.cgst for line in invoice.lines)
        total_sgst = sum(line.sgst for line in invoice.lines)
        total_igst = sum(line.igst for line in invoice.lines)
        
        # Calculate round off (Grand Total - (Taxable + Tax))
        sum_components = invoice.total_taxable_amount + invoice.total_tax
        round_off = round(invoice.grand_total - sum_components, 2)
        
        return template.render(
            invoice=invoice,
            voucher_type=self.config.default_voucher_type or "Sales",
            customer_ledger_name=self._resolve_ledger(invoice.customer_name or "Cash"),
            resolve_product=self._resolve_product,
            resolve_ledger=self._resolve_ledger,
            default_sales_ledger=self.config.default_sales_ledger or "Sales",
            default_godown=self.config.default_godown or "Main Location",
            default_round_off_ledger=self.config.round_off_ledger or "Round Off",
            total_cgst=total_cgst,
            total_sgst=total_sgst,
            total_igst=total_igst,
            round_off=round_off
        )

    def generate_invoice_export(self, invoices: List[InvoiceDTO]) -> AccountingExportResult:
        try:
            rendered_vouchers = [self._render_invoice(inv) for inv in invoices]
            
            # Note: Need the real company name to map
            company_ref = str(self.company_id) # Should be company code
            tally_company_name = self._resolve_company(company_ref)
            
            envelope_template = self.jinja_env.get_template("envelope.xml.j2")
            final_xml = envelope_template.render(
                company_name=tally_company_name,
                vouchers=rendered_vouchers
            )
            
            return AccountingExportResult(
                success=True,
                payload=final_xml
            )
        except Exception as e:
            return AccountingExportResult(
                success=False,
                error_message=str(e)
            )

    def generate_master_export(self, master_type: str, entities: List[dict]) -> AccountingExportResult:
        # To be implemented for Master Sync
        return AccountingExportResult(success=True, payload="<xml></xml>")
