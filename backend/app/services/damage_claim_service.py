from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.schema import DamageClaim, Product, Warehouse
from app.services.inventory_event_engine import InventoryEventEngine
from pydantic import BaseModel
from typing import List, Optional

class CreateDamageClaimRequest(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int
    video_reference: Optional[str] = None
    remarks: Optional[str] = None

class DamageClaimService:
    @staticmethod
    def _generate_claim_number(db: Session, hub_code: str) -> str:
        count = db.query(DamageClaim).count() + 1
        return f"DMG/{hub_code}/26-27/{count:05d}"

    @staticmethod
    def create_claim(db: Session, company_id: int, request: CreateDamageClaimRequest, user_id: int):
        warehouse = db.query(Warehouse).filter(Warehouse.id == request.warehouse_id, Warehouse.company_id == company_id).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
            
        hub_code = warehouse.hub.hub_code if warehouse.hub else "FC"
        claim_num = DamageClaimService._generate_claim_number(db, hub_code)
        
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
        product = db.query(Product).filter(Product.id == request.product_id).first()
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
        
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def update_claim_status(db: Session, company_id: int, claim_id: int, status: str, user_id: int):
        if status not in ["Approved", "Rejected"]:
            raise HTTPException(status_code=400, detail="Invalid status update")
            
        claim = db.query(DamageClaim).filter(DamageClaim.id == claim_id, DamageClaim.company_id == company_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        if claim.claim_status != "Pending":
            raise HTTPException(status_code=400, detail=f"Claim is already {claim.claim_status}")
            
        product = db.query(Product).filter(Product.id == claim.product_id).first()
        
        if status == "Approved":
            # Approved: Stock is permanently written off. Remove from reserved. 
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
        db.commit()
        db.refresh(claim)
        return claim
