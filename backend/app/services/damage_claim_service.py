from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import date
from app.models.schema import DamageClaim, Product, Warehouse, DocumentTypeEnum
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.document_number_service import DocumentNumberService
from pydantic import BaseModel
from app.services.audit_log_service import AuditLogService
from typing import Optional

class CreateDamageClaimRequest(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int
    video_reference: Optional[str] = None
    remarks: Optional[str] = None

def _get_fiscal_year_string(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"

class DamageClaimService:
    @staticmethod
    def _generate_claim_number(db: Session, hub_code: str, company_id: int) -> str:
        fy = _get_fiscal_year_string(date.today())
        prefix = f"DMG/{hub_code}"
        return DocumentNumberService.generate_number(
            db=db,
            company_id=company_id,
            document_type=DocumentTypeEnum.DAMAGE,
            fiscal_year=fy,
            prefix_override=prefix
        )

    @staticmethod
    def create_claim(db: Session, company_id: int, request: CreateDamageClaimRequest, user_id: int):
        warehouse = db.query(Warehouse).filter(Warehouse.id == request.warehouse_id, Warehouse.company_id == company_id).first()
        print(f"[COMPANY FILTER] Warehouse, {company_id}")
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
            
        hub_code = warehouse.hub.hub_code if warehouse.hub else "FC"
        claim_num = DamageClaimService._generate_claim_number(db, hub_code, company_id)
        
        claim = DamageClaim(
            company_id=company_id,
            warehouse_id=request.warehouse_id,
            product_id=request.product_id,
            claim_number=claim_num,
            quantity=request.quantity,
            video_reference=request.video_reference,
            remarks=request.remarks,
            claim_status="Pending",
            created_by=user_id
        )
        db.add(claim)
        db.flush()
        
        # Lock Inventory: Move from available to reserved
        product = db.query(Product).filter(Product.id == request.product_id, Product.company_id == company_id).first()
        print(f"[COMPANY FILTER] Product, {company_id}")
        InventoryEventEngine.process_event(
            db=db,
            company_id=company_id,
            product_sku=product.sku,
            warehouse_id=request.warehouse_id,
            quantity=request.quantity,
            event_type="RESERVED",
            source="DAMAGE_CLAIM",
            reference_id=claim_num,
            metadata_payload={"damage_claim_id": claim.id}
        )
        
        db.flush()
        db.refresh(claim)
        return claim

    @staticmethod
    def update_claim_status(db: Session, company_id: int, claim_id: int, status: str, user_id: int):
        status = status.strip().title()  # Normalize: 'APPROVED' -> 'Approved'
        
        claim = db.query(DamageClaim).filter(DamageClaim.id == claim_id, DamageClaim.company_id == company_id).with_for_update().first()
        
        print({
            "incoming_status": status,
            "current_status": claim.claim_status if claim else None,
            "allowed": ["Pending -> Approved", "Pending -> Rejected"]
        })
        
        if status not in ["Approved", "Rejected"]:
            raise HTTPException(status_code=400, detail="Invalid status update")
            
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        if claim.claim_status.lower() != "pending":
            raise HTTPException(status_code=400, detail=f"Claim is already {claim.claim_status}")
            
        product = db.query(Product).filter(Product.id == claim.product_id, Product.company_id == company_id).first()
        
        if status == "Approved":
            # Approved: Stock is permanently written off. Remove from reserved. 
            
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=product.sku,
                warehouse_id=claim.warehouse_id,
                quantity=claim.quantity,
                event_type="UNRESERVE",
                source="DAMAGE_CLAIM_APPROVED",
                reference_id=claim.claim_number,
                metadata_payload={"damage_claim_id": claim.id}
            )

            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=product.sku,
                warehouse_id=claim.warehouse_id,
                quantity=claim.quantity,
                event_type="DAMAGE_WRITE_OFF",
                source="DAMAGE_CLAIM_APPROVED",
                reference_id=claim.claim_number,
                metadata_payload={"damage_claim_id": claim.id}
            )
            
        elif status == "Rejected":
            # Rejected: Stock is unlocked and returned to available
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=product.sku,
                warehouse_id=claim.warehouse_id,
                quantity=claim.quantity,
                event_type="UNRESERVE",
                source="DAMAGE_CLAIM_REJECTED",
                reference_id=claim.claim_number,
                metadata_payload={"damage_claim_id": claim.id}
            )
            
        claim.claim_status = status
        
        AuditLogService.log(
            db,
            company_id=company_id,
            entity_type="DamageClaim",
            entity_id=claim.id,
            event_type=f"CLAIM_{status.upper()}",
            message=f"Damage claim {claim.claim_number} {status.lower()}",
            metadata={"product_id": claim.product_id, "quantity": claim.quantity, "user_id": user_id}
        )
        
        db.flush()
        db.refresh(claim)
        return claim
