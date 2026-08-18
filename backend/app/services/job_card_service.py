from sqlalchemy.orm import Session, joinedload
from app.models.schema import JobCard, JobCardItem, DocumentTypeEnum, Product
from app.schemas.service import JobCardCreate, JobCardDirectCreate, JobCardUpdateStatus
from app.services.document_number_service import DocumentNumberService
from fastapi import HTTPException
from datetime import datetime

class JobCardService:
    def __init__(self, db: Session):
        self.db = db

    def create_direct_job_card(self, company_id: int, data: JobCardDirectCreate, user_id: int) -> JobCard:
        # Validate complaint is meaningful
        if not data.complaint or len(data.complaint.strip()) < 5:
            raise HTTPException(status_code=400, detail="Complaint description must be at least 5 characters")

        # Validate items are present
        if not data.items or len(data.items) == 0:
            raise HTTPException(status_code=400, detail="At least one service item is required")
            
        if not data.product_name or len(data.product_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Product name is required")

        for item in data.items:
            if item.qty <= 0 or item.qty > 1000:
                raise HTTPException(status_code=400, detail="Invalid qty")
            if item.rate < 0:
                raise HTTPException(status_code=400, detail="Invalid rate")
            if item.product_sku:
                item.source = "product"
            else:
                item.source = "manual"

        now = datetime.utcnow()
        year = now.year
        if now.month >= 4:
            fy_str = f"{str(year)[-2:]}-{str(year+1)[-2:]}"
        else:
            fy_str = f"{str(year-1)[-2:]}-{str(year)[-2:]}"

        # 1. Create underlying ServiceRecord (to maintain DB integrity)
        from app.services.service_record_service import ServiceRecordService
        service_num = ServiceRecordService._generate_service_number(self.db, company_id)
        
        from app.models.schema import ServiceRecord
        db_service_record = ServiceRecord(
            company_id=company_id,
            service_number=service_num,
            customer_name_snapshot=data.customer_name,
            customer_mobile_snapshot=data.customer_mobile,
            source_type=data.source_type,
            source_invoice_id=data.source_invoice_id,
            machine_type=data.product_name,
            brand=data.brand,
            complaint=data.complaint,
            service_type=data.service_type,
            service_location=data.service_location,
            status="Pending",
            created_by=user_id,
            service_date=now
        )
        self.db.add(db_service_record)
        self.db.flush()

        # 2. Create JobCard
        job_card_number = DocumentNumberService.generate_number(self.db, company_id, DocumentTypeEnum.JOB_CARD, fy_str)
        
        db_job_card = JobCard(
            company_id=company_id,
            service_record_id=db_service_record.id,
            job_card_number=job_card_number,
            workshop_id=data.workshop_id,
            assigned_to=data.assigned_to,
            status="OPEN"
        )
        self.db.add(db_job_card)
        self.db.flush()

        # 3. Create JobCardItems
        for item in data.items:
            if item.product_sku:
                real_product = self.db.query(Product).filter(
                    Product.sku == item.product_sku.strip().upper(),
                    Product.company_id == company_id
                ).first()
                if real_product:
                    resolved_item_name = real_product.name
                else:
                    resolved_item_name = item.item_name
            else:
                resolved_item_name = item.item_name

            db_item = JobCardItem(
                job_card_id=db_job_card.id,
                source=item.source,
                source_invoice_item_id=item.source_invoice_item_id,
                item_name=resolved_item_name,
                product_sku=item.product_sku,
                qty=item.qty,
                rate=item.rate,
                amount=item.qty * item.rate
            )
            self.db.add(db_item)
            
        self.db.commit()
        self.db.refresh(db_job_card)
        return db_job_card

    def create_job_card(self, company_id: int, job_card_data: JobCardCreate) -> JobCard:
        # Validate complaint is meaningful (if present)
        if hasattr(job_card_data, 'complaint'):
            if not job_card_data.complaint or len(job_card_data.complaint.strip()) < 5:
                raise HTTPException(status_code=400, detail="Complaint description must be at least 5 characters")

        # Validate items are present
        if not job_card_data.items or len(job_card_data.items) == 0:
            raise HTTPException(status_code=400, detail="At least one service item is required")

        # Verify ServiceRecord exists
        from app.models.schema import ServiceRecord
        service_record = self.db.query(ServiceRecord).filter(
            ServiceRecord.id == job_card_data.service_record_id,
            ServiceRecord.company_id == company_id
        ).first()
        
        if not service_record:
            raise HTTPException(status_code=404, detail="Service Record not found")

        for item in job_card_data.items:
            if item.qty <= 0 or item.qty > 1000:
                raise HTTPException(status_code=400, detail="Invalid qty")
            if item.rate < 0:
                raise HTTPException(status_code=400, detail="Invalid rate")
            if item.product_sku:
                item.source = "product"
            else:
                item.source = "manual"

        # Determine Fiscal Year
        now = datetime.utcnow()
        year = now.year
        if now.month >= 4:
            fy_str = f"{str(year)[-2:]}-{str(year+1)[-2:]}"
        else:
            fy_str = f"{str(year-1)[-2:]}-{str(year)[-2:]}"

        # Generate atomic job card number
        job_card_number = DocumentNumberService.generate_number(self.db, company_id, DocumentTypeEnum.JOB_CARD, fy_str)
        
        db_job_card = JobCard(
            company_id=company_id,
            service_record_id=job_card_data.service_record_id,
            job_card_number=job_card_number,
            workshop_id=job_card_data.workshop_id,
            assigned_to=job_card_data.assigned_to,
            status="OPEN"
        )
        self.db.add(db_job_card)
        self.db.flush()

        for item in job_card_data.items:
            if item.product_sku:
                real_product = self.db.query(Product).filter(
                    Product.sku == item.product_sku.strip().upper(),
                    Product.company_id == company_id
                ).first()
                if real_product:
                    resolved_item_name = real_product.name
                else:
                    resolved_item_name = item.item_name
            else:
                resolved_item_name = item.item_name

            db_item = JobCardItem(
                job_card_id=db_job_card.id,
                source=item.source,
                source_invoice_item_id=item.source_invoice_item_id,
                item_name=resolved_item_name,
                product_sku=item.product_sku,
                qty=item.qty,
                rate=item.rate,
                amount=item.qty * item.rate
            )
            self.db.add(db_item)
            
        self.db.commit()
        self.db.refresh(db_job_card)
        return db_job_card

    def get_job_cards(self, company_id: int):
        return self.db.query(JobCard).options(joinedload(JobCard.service_record)).filter(JobCard.company_id == company_id).all()

    def get_job_card(self, company_id: int, job_card_id: int):
        job_card = self.db.query(JobCard).options(joinedload(JobCard.service_record)).filter(
            JobCard.id == job_card_id, 
            JobCard.company_id == company_id
        ).first()
        if not job_card:
            raise HTTPException(status_code=404, detail="Job Card not found")
        return job_card

    def update_status(self, company_id: int, job_card_id: int, status_data: JobCardUpdateStatus):
        job_card = self.get_job_card(company_id, job_card_id)
        
        allowed_transitions = {
            "OPEN": ["IN_PROGRESS"],
            "IN_PROGRESS": ["COMPLETED"],
            "COMPLETED": [],
            "LOCKED": []
        }
        
        if job_card.status == "LOCKED":
            raise HTTPException(status_code=400, detail="Cannot edit a LOCKED job card")
            
        if status_data.status == "LOCKED":
            raise HTTPException(status_code=400, detail="LOCKED status can only be set internally via Invoice generation")
            
        if status_data.status not in allowed_transitions.get(job_card.status, []):
            raise HTTPException(status_code=400, detail=f"Invalid transition from {job_card.status} to {status_data.status}")

        # Prevent completing a job card with no items
        if status_data.status == "COMPLETED":
            if not job_card.items or len(job_card.items) == 0:
                raise HTTPException(status_code=400, detail="Cannot complete a job card with no service items")
            total_amount = sum((item.amount or 0) for item in job_card.items)
            if total_amount <= 0:
                raise HTTPException(status_code=400, detail="Cannot complete a job card with zero total amount")

        job_card.status = status_data.status
        self.db.commit()
        self.db.refresh(job_card)
        return job_card
