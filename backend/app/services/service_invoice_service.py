from sqlalchemy.orm import Session, joinedload
from app.models.schema import ServiceInvoice, ServiceInvoiceItem, Product, DocumentTypeEnum, JobCard
from app.schemas.service import ServiceInvoiceCreate
from app.services.document_number_service import DocumentNumberService
from app.services.inventory_event_engine import InventoryEventEngine
from fastapi import HTTPException
from datetime import datetime

class ServiceInvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def generate_invoice(self, company_id: int, invoice_data: ServiceInvoiceCreate, user_id: int = None) -> ServiceInvoice:
        # Prevent Duplicate Invoice
        existing_invoice = self.db.query(ServiceInvoice).filter(
            ServiceInvoice.company_id == company_id,
            ServiceInvoice.job_card_id == invoice_data.job_card_id
        ).first()
        if existing_invoice:
            raise HTTPException(status_code=409, detail=f"An invoice already exists for Job Card ID {invoice_data.job_card_id}.")

        from app.services.job_card_service import JobCardService
        job_card = self.db.query(JobCard).filter(
            JobCard.id == invoice_data.job_card_id, 
            JobCard.company_id == company_id
        ).with_for_update().first()
        
        if not job_card:
            raise HTTPException(status_code=404, detail="Job Card not found")
            
        if job_card.status != "COMPLETED":
            raise HTTPException(status_code=400, detail="Invoice can only be generated for COMPLETED job cards.")
            
        if not job_card.items:
            raise HTTPException(status_code=400, detail="No items to invoice")

        # Determine Fiscal Year
        now = datetime.utcnow()
        year = now.year
        if now.month >= 4:
            fy_str = f"{str(year)[-2:]}-{str(year+1)[-2:]}"
        else:
            fy_str = f"{str(year-1)[-2:]}-{str(year)[-2:]}"

        # Generate atomic invoice number
        invoice_number = DocumentNumberService.generate_number(self.db, company_id, DocumentTypeEnum.SERVICE_INVOICE, fy_str)
        
        workshop_id = job_card.workshop_id

        calc_total_amount = 0.0
        calc_cgst_amount = 0.0
        calc_sgst_amount = 0.0
        
        # Build invoice items from JobCardItems (Snapshot Isolation)
        invoice_items_to_create = []
        
        for idx, item in enumerate(job_card.items):
            # Fallback to frontend payload for GST rate / HSN if we wanted, but we will fetch from product if possible
            # To keep it simple and strictly server side:
            gst_rate = 18.0 # Default service GST
            hsn = "9987" # Default service HSN
            
            if item.product_sku:
                product = self.db.query(Product).filter(
                    Product.company_id == company_id,
                    Product.sku == item.product_sku
                ).first()
                if product:
                    gst_rate = product.default_gst_rate if product.default_gst_rate is not None else 18.0
                    hsn = product.hsn_code if product.hsn_code else "9987"
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid Product SKU: {item.product_sku}")

            base_amt = item.qty * item.rate
            calc_total_amount += base_amt
            gst_amt = base_amt * (gst_rate / 100.0)
            calc_cgst_amount += gst_amt / 2.0
            calc_sgst_amount += gst_amt / 2.0
            
            invoice_items_to_create.append({
                "description": item.item_name,
                "product_sku": item.product_sku,
                "hsn": hsn,
                "gst_rate": gst_rate,
                "qty": item.qty,
                "rate": item.rate,
                "amount": base_amt,
                "idx": idx
            })

        calc_grand_total = round(calc_total_amount + calc_cgst_amount + calc_sgst_amount)

        db_invoice = ServiceInvoice(
            company_id=company_id,
            invoice_number=invoice_number,
            job_card_id=job_card.id,
            total_amount=calc_total_amount,
            cgst_amount=calc_cgst_amount,
            sgst_amount=calc_sgst_amount,
            grand_total=calc_grand_total,
            created_by=user_id
        )
        self.db.add(db_invoice)
        
        # Update Job Card Status
        job_card.status = "LOCKED"
        
        self.db.flush()

        try:
            with self.db.begin_nested():
                for item_data in invoice_items_to_create:
                    db_item = ServiceInvoiceItem(
                        invoice_id=db_invoice.id,
                        description=item_data["description"],
                        product_sku=item_data["product_sku"],
                        hsn=item_data["hsn"],
                        gst_rate=item_data["gst_rate"],
                        qty=item_data["qty"],
                        rate=item_data["rate"],
                        amount=item_data["amount"]
                    )
                    self.db.add(db_item)
                    
                    if item_data["product_sku"]:
                        op_id = f"INV_SVC_{job_card.id}_{item_data['product_sku']}_{item_data['idx']}"
                        
                        InventoryEventEngine.process_event(
                            db=self.db,
                            company_id=company_id,
                            product_sku=item_data["product_sku"],
                            warehouse_id=workshop_id,
                            quantity=item_data["qty"],
                            event_type="DEDUCT",
                            source="SERVICE_INVOICE",
                            reference_id=str(db_invoice.id),
                            user_id=user_id,
                            metadata_payload={"operation_id": op_id}
                        )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Failed to process inventory deduction: {str(e)}")

        self.db.commit()
        self.db.refresh(db_invoice)
        return db_invoice

    def get_invoices(self, company_id: int):
        return self.db.query(ServiceInvoice).options(
            joinedload(ServiceInvoice.job_card).joinedload(JobCard.service_record)
        ).filter(ServiceInvoice.company_id == company_id).all()

    def get_invoice(self, company_id: int, invoice_id: int):
        invoice = self.db.query(ServiceInvoice).options(
            joinedload(ServiceInvoice.job_card).joinedload(JobCard.service_record)
        ).filter(
            ServiceInvoice.id == invoice_id, 
            ServiceInvoice.company_id == company_id
        ).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Service Invoice not found")
        return invoice
