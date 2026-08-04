import os
import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.schema import Sale, Company
from app.models.accounting_schema import AccountingExportBatch, AccountingExportLog
from app.services.accounting.dtos import InvoiceDTO, InvoiceLineDTO
from app.services.accounting.tally_connector import TallyXMLConnector

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "exports", "accounting")

class AccountingIntegrationEngine:
    def __init__(self, db: Session, company_id: int):
        self.db = db
        self.company_id = company_id
        self.connector = TallyXMLConnector(db, company_id)
        
        # Ensure export directory exists
        os.makedirs(EXPORT_DIR, exist_ok=True)

    def _build_invoice_dto(self, sale: Sale) -> InvoiceDTO:
        lines = []
        for item in sale.items:
            lines.append(InvoiceLineDTO(
                product_sku=item.sku,
                product_name=item.product_name or item.product.name,
                hsn_sac=item.hsn_sac or item.product.hsn_code,
                quantity=item.quantity,
                unit=item.unit or item.product.unit,
                rate=item.selling_price,
                line_total=item.line_total,
                taxable_amount=item.taxable_amount,
                discount=item.discount,
                cgst=item.cgst,
                sgst=item.sgst,
                igst=item.igst
            ))
            
        return InvoiceDTO(
            sale_id=sale.id,
            invoice_number=sale.invoice_number or sale.bill_number,
            invoice_date=sale.sale_date,
            invoice_type=sale.invoice_type,
            customer_name=sale.customer_name,
            customer_gstin=sale.customer_gstin,
            customer_state=sale.customer_state,
            customer_address=sale.customer_address,
            place_of_supply=sale.place_of_supply,
            total_taxable_amount=sale.total_taxable_amount,
            total_tax=sale.total_tax,
            grand_total=sale.grand_total,
            lines=lines,
            company_id=self.company_id
        )

    def _validate_dto(self, dto: InvoiceDTO) -> List[str]:
        errors = []
        if not dto.customer_name:
            errors.append("Customer name is missing.")
        if dto.grand_total <= 0:
            errors.append("Invoice total must be > 0.")
        # Check Dr=Cr
        sum_components = round(dto.total_taxable_amount + dto.total_tax, 2)
        diff = round(abs(dto.grand_total - sum_components), 2)
        if diff > 1.0: # allow up to 1 rupee roundoff
            errors.append(f"Taxable + Tax does not match Grand Total. Diff: {diff}")
        return errors

    def export_invoices(self, sale_ids: List[int], user_id: Optional[int] = None) -> AccountingExportBatch:
        sales = self.db.query(Sale).filter(Sale.id.in_(sale_ids), Sale.company_id == self.company_id).all()
        
        batch = AccountingExportBatch(
            company_id=self.company_id,
            batch_type="Invoices",
            generated_by=user_id,
            invoice_count=len(sales),
            status="Queued",
            template_version="v1",
            erp_version="1.0.0"
        )
        self.db.add(batch)
        self.db.flush() # get batch ID
        
        dtos_to_export = []
        logs = []
        
        for sale in sales:
            dto = self._build_invoice_dto(sale)
            validation_errors = self._validate_dto(dto)
            
            log = AccountingExportLog(
                company_id=self.company_id,
                batch_id=batch.id,
                sale_id=sale.id,
                status="Generated" if not validation_errors else "Failed",
                last_error=", ".join(validation_errors) if validation_errors else None
            )
            self.db.add(log)
            logs.append(log)
            
            if not validation_errors:
                dtos_to_export.append(dto)
        
        if not dtos_to_export:
            batch.status = "Failed"
            batch.errors = "All invoices failed validation."
            self.db.commit()
            return batch
            
        batch.status = "Generating"
        self.db.commit()
            
        result = self.connector.generate_invoice_export(dtos_to_export)
        
        if result.success and result.payload:
            # Save XML to disk
            filename = f"batch_{batch.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
            file_path = os.path.join(EXPORT_DIR, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result.payload)
                
            checksum = hashlib.sha256(result.payload.encode('utf-8')).hexdigest()
            
            # Save Manifest
            manifest = {
                "batch": f"BATCH-{datetime.now().strftime('%Y%m%d')}-{batch.id:03d}",
                "template": batch.template_version,
                "erp_version": batch.erp_version,
                "generated_at": datetime.now().isoformat(),
                "invoice_count": batch.invoice_count,
                "total_value": sum(d.grand_total for d in dtos_to_export),
                "checksum": checksum
            }
            manifest_path = file_path.replace('.xml', '_manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
                
            batch.file_path = file_path
            batch.checksum_sha256 = checksum
            batch.status = "Generated" # Ready to be 'Downloaded'
            for log in logs:
                if log.status == "Generated":
                    log.last_export_time = datetime.utcnow()
        else:
            batch.status = "Failed"
            batch.errors = result.error_message
            for log in logs:
                log.status = "Failed"
                if not log.last_error:
                    log.last_error = "Batch generation failed."

        self.db.commit()
        return batch
