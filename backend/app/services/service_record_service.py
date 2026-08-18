from sqlalchemy.orm import Session
from datetime import datetime
from app.models.schema import ServiceRecord, ServiceRecordItem, Sale, Product
from app.models.schema import Company

class ServiceRecordService:
    @staticmethod
    def _generate_service_number(db: Session, company_id: int) -> str:
        from app.services.document_number_service import DocumentNumberService
        from app.models.schema import DocumentTypeEnum
        now = datetime.utcnow()
        year = now.year
        month = now.month
        
        # Simple FY logic: Apr-Mar
        if month >= 4:
            fy_str = f"{str(year)[-2:]}-{str(year+1)[-2:]}"
        else:
            fy_str = f"{str(year-1)[-2:]}-{str(year)[-2:]}"
            
        company = db.query(Company).filter(Company.id == company_id).first()
        company_prefix = company.code if company and company.code else f"COMP{company_id}"
        return DocumentNumberService.generate_number(
            db, company_id, DocumentTypeEnum.SERVICE, fy_str, prefix_override=f"{company_prefix}/SRV"
        )

    @staticmethod
    def create_record(db: Session, company_id: int, data: dict, user_id: int = None) -> ServiceRecord:
        service_num = ServiceRecordService._generate_service_number(db, company_id)
        
        # If customer_id provided, fetch snapshots
        customer_id = data.get("customer_id")
        customer_name_snapshot = data.get("customer_name_snapshot", "Walk-in")
        customer_mobile_snapshot = data.get("customer_mobile_snapshot")
        customer_email_snapshot = data.get("customer_email_snapshot")
        
        if customer_id:
            # We assume customer_id refers to a Sale in this phase
            sale = db.query(Sale).filter(Sale.id == customer_id).first()
            if sale:
                customer_name_snapshot = sale.customer_name or customer_name_snapshot
                customer_mobile_snapshot = sale.customer_mobile or customer_mobile_snapshot
                customer_email_snapshot = sale.customer_email or customer_email_snapshot
                
        record = ServiceRecord(
            company_id=company_id,
            service_number=service_num,
            customer_id=customer_id,
            customer_name_snapshot=customer_name_snapshot,
            customer_mobile_snapshot=customer_mobile_snapshot,
            customer_email_snapshot=customer_email_snapshot,
            customer_address_snapshot=data.get("customer_address_snapshot"),
            source_type=data.get("source_type", "manual"),
            source_invoice_id=data.get("source_invoice_id"),
            invoice_number=data.get("invoice_number"),
            sale_type=data.get("sale_type"),
            marketplace=data.get("marketplace"),
            service_date=data.get("service_date", datetime.utcnow()),
            service_type=data.get("service_type"),
            machine_type=data.get("machine_type"),
            brand=data.get("brand"),
            power_type=data.get("power_type"),
            warranty=data.get("warranty", False),
            service_location=data.get("service_location"),
            complaint=data.get("complaint"),
            technician_notes=data.get("technician_notes"),
            status="Pending",
            created_by=user_id
        )
        db.add(record)
        db.flush()
        
        items_data = data.get("items", [])
        for item in items_data:
            product_id = item.get("product_id")
            sku_snapshot = item.get("sku_snapshot")
            
            if product_id and not sku_snapshot:
                prod = db.query(Product).filter(Product.id == product_id).first()
                if prod:
                    sku_snapshot = prod.sku
                    
            record_item = ServiceRecordItem(
                service_record_id=record.id,
                product_id=product_id,
                sku_snapshot=sku_snapshot,
                quantity=item.get("quantity", 1),
                serial_number=item.get("serial_number")
            )
            db.add(record_item)
            
        db.flush()
        return record

    @staticmethod
    def update_status(db: Session, company_id: int, record_id: int, status: str, technician_notes: str = None) -> ServiceRecord:
        record = db.query(ServiceRecord).filter(
            ServiceRecord.id == record_id, 
            ServiceRecord.company_id == company_id
        ).first()
        
        if not record:
            raise ValueError("Service record not found")
            
        if record.status in ["Completed", "Cancelled"]:
            raise ValueError(f"Cannot update a {record.status} service record")
            
        if status not in ["Pending", "In Progress", "Completed", "Cancelled"]:
            raise ValueError("Invalid status")
            
        record.status = status
        if technician_notes is not None:
            record.technician_notes = technician_notes
            
        # Cascade status to linked Job Cards
        job_card_status_map = {
            "Pending": "OPEN",
            "In Progress": "IN_PROGRESS",
            "Completed": "COMPLETED",
            "Cancelled": "CANCELLED"
        }
        mapped_status = job_card_status_map.get(status)
        if mapped_status:
            for jc in record.job_cards:
                jc.status = mapped_status
            
        db.flush()
        return record

    @staticmethod
    def record_replacement(db: Session, company_id: int, item_id: int, replacement_product_id: int, quantity: int) -> ServiceRecordItem:
        item = db.query(ServiceRecordItem).join(ServiceRecord).filter(
            ServiceRecordItem.id == item_id,
            ServiceRecord.company_id == company_id
        ).first()
        
        if not item:
            raise ValueError("Service item not found")
            
        if item.service_record.status in ["Completed", "Cancelled"]:
            raise ValueError(f"Cannot edit replacements for a {item.service_record.status} record")
            
        item.replacement_product_id = replacement_product_id
        item.replacement_quantity = quantity
        db.flush()
        return item
        
    @staticmethod
    def update_bill(db: Session, company_id: int, record_id: int, labour_charges: float, spare_charges: float, tax_amount: float) -> ServiceRecord:
        record = db.query(ServiceRecord).filter(
            ServiceRecord.id == record_id, 
            ServiceRecord.company_id == company_id
        ).first()
        
        if not record:
            raise ValueError("Service record not found")
            
        if record.status in ["Completed", "Cancelled"]:
            raise ValueError(f"Cannot update billing for a {record.status} service record")
            
        record.labour_charges = labour_charges
        record.spare_charges = spare_charges
        record.tax_amount = tax_amount
        record.grand_total = labour_charges + spare_charges + tax_amount
        db.flush()
        return record
