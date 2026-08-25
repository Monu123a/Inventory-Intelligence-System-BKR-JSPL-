import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, exc
from pydantic import BaseModel, Field

from app.models.schema import (
    Company, User, Product, Warehouse, Inventory, InventoryMovement,
    Vendor, Purchase, PurchaseItem, OfflinePurchase, CompanySettings, VendorTransaction
)
from app.services.document_number_service import DocumentNumberService, DocumentTypeEnum
from app.services.inventory_event_engine import InventoryEventEngine

logger = logging.getLogger(__name__)

# Strict SKU Regex Rule
SKU_PATTERN = re.compile(r'\b[A-Za-z]{2}\d{4}[0-9\-]*\b')

def strict_normalize_sku(raw_sku: str) -> Optional[str]:
    """
    Normalizes a SKU using the strict AGENTS.md regex.
    Returns the valid extracted SKU, or None if no match.
    """
    raw_sku = raw_sku.strip().upper()
    match = SKU_PATTERN.search(raw_sku)
    if match:
        return match.group(0)
    return None

class PurchaseItemRequest(BaseModel):
    product_sku: str
    product_id: Optional[int] = None
    description: Optional[str] = None
    qty: float = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    gst_pct: float = Field(..., ge=0)
    hsn: Optional[str] = None
    
    # Optional fields for inline product creation
    brand: Optional[str] = "N/A"
    category: Optional[str] = "N/A"
    create_inline: bool = False

class PurchaseDraftRequest(BaseModel):
    idempotency_key: str
    company_id: int
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    items: List[PurchaseItemRequest]
    notes: Optional[str] = None
    warehouse_id: Optional[int] = None

class PurchaseReceiveRequest(BaseModel):
    idempotency_key: str
    warehouse_id: Optional[int] = None


class PurchasePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    method: str
    txn_ref: Optional[str] = None
    notes: Optional[str] = None

class PurchaseService:
    @staticmethod
    def _get_or_create_vendor(db: Session, company_id: int, vendor_id: Optional[int], vendor_name: Optional[str]) -> Vendor:
        if vendor_id:
            vendor = db.query(Vendor).filter_by(id=vendor_id, company_id=company_id).first()
            if vendor:
                return vendor
        
        if not vendor_name:
            raise ValueError("Must provide either a valid vendor_id or vendor_name")
            
        # Try to find by name exactly
        vendor = db.query(Vendor).filter_by(name=vendor_name, company_id=company_id).first()
        if not vendor:
            vendor = Vendor(name=vendor_name, company_id=company_id)
            db.add(vendor)
            db.flush()
        return vendor
        
    @staticmethod
    def create_draft(db: Session, request: PurchaseDraftRequest, operator_id: int) -> dict:
        # Idempotency check
        existing = db.query(Purchase).filter_by(company_id=request.company_id, idempotency_key=request.idempotency_key).first()
        if existing:
            return {"id": existing.id, "status": existing.status, "message": "Returned cached draft"}
            
        vendor = PurchaseService._get_or_create_vendor(db, request.company_id, request.vendor_id, request.vendor_name)
        
        purchase = Purchase(
            vendor_id=vendor.id,
            company_id=request.company_id,
            operator_id=operator_id,
            status="DRAFT",
            invoice_number=request.invoice_number if request.invoice_number else None,
            idempotency_key=request.idempotency_key,
            notes=request.notes
        )
        db.add(purchase)
        db.flush()
        
        total_amount = 0.0
        
        for item_req in request.items:
            norm_sku = strict_normalize_sku(item_req.product_sku) or item_req.product_sku.strip().upper()
            
            line_total = item_req.qty * item_req.unit_cost
            total_amount += line_total
            
            product_id = item_req.product_id
            
            p_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=product_id,
                product_sku=norm_sku,
                description=item_req.description,
                qty=item_req.qty,
                unit_cost=item_req.unit_cost,
                gst_pct=item_req.gst_pct,
                hsn=item_req.hsn,
                line_total=line_total
            )
            db.add(p_item)
            
        purchase.total_amount = total_amount
        db.flush()
        
        return {"id": purchase.id, "status": purchase.status, "total_amount": total_amount}

    @staticmethod
    def get_default_warehouse(db: Session, company_id: int) -> Optional[int]:
        wh = db.query(Warehouse).filter_by(company_id=company_id, status="ACTIVE").filter(
            Warehouse.name.ilike('%central%') | Warehouse.name.ilike('%bkr%')
        ).first()
        if wh:
            return wh.id
        # Fallback to any active warehouse
        wh = db.query(Warehouse).filter_by(company_id=company_id, status="ACTIVE").first()
        return wh.id if wh else None

    @staticmethod
    def receive_purchase(db: Session, purchase_id: int, request: PurchaseReceiveRequest, operator_id: int) -> dict:
        purchase = db.query(Purchase).filter_by(id=purchase_id).first()
        if not purchase:
            raise ValueError("Purchase not found")
            
        if purchase.status != "DRAFT":
            # If already received and it's a replay with same key, return success idempotently
            if purchase.idempotency_key == request.idempotency_key or purchase.status == "RECEIVED":
                 return {"synced": True, "purchase_id": purchase.id, "message": "Already received"}
            raise ValueError(f"Cannot receive purchase in {purchase.status} state")

        warehouse_id = request.warehouse_id or PurchaseService.get_default_warehouse(db, purchase.company_id)
        if not warehouse_id:
            raise ValueError("Target warehouse must be provided or default configured")
            
        # Validate warehouse belongs to company
        wh = db.query(Warehouse).filter_by(id=warehouse_id, company_id=purchase.company_id).first()
        if not wh:
            raise ValueError("Target warehouse does not belong to this company")

        movements = []
        
        for item in purchase.items:
            # Inline Product Creation Logic
            if not item.product_id:
                # Need to auto-create product. 
                # Find matching product by SKU in DB first to be safe
                existing_product = db.query(Product).filter_by(company_id=purchase.company_id, sku=item.product_sku).first()
                if existing_product:
                    item.product_id = existing_product.id
                else:
                    new_product = Product(
                        company_id=purchase.company_id,
                        name=item.description or f"Product {item.product_sku}",
                        sku=item.product_sku,
                        brand="N/A",
                        category="N/A",
                        hsn=item.hsn,
                        status="DRAFT" # Needs review later
                    )
                    db.add(new_product)
                    db.flush()
                    item.product_id = new_product.id
                    logger.info(f"Inline created product {new_product.sku}")

            # Inventory Update with InventoryEventEngine
            mov = InventoryEventEngine.process_event(
                db=db,
                company_id=purchase.company_id,
                product_sku=item.product_sku,
                warehouse_id=warehouse_id,
                quantity=item.qty,
                event_type="ADD",
                source="PURCHASE",
                reference_id=purchase.invoice_number or f"PUR-{purchase.id}",
                user_id=operator_id,
                metadata_payload={"operation_id": f"RECV_{purchase.id}_{item.id}_{request.idempotency_key}"}
            )
            movements.append(mov)

        # Update Payables and Ledger
        vendor = purchase.vendor
        vendor.payable_balance = float(vendor.payable_balance or 0) + float(purchase.total_amount)
        
        vt = VendorTransaction(
            vendor_id=vendor.id,
            transaction_type='INVOICE',
            amount=purchase.total_amount,
            ref_purchase_id=purchase.id,
            notes=f"Invoice {purchase.invoice_number or purchase.id}"
        )
        db.add(vt)

        purchase.status = "RECEIVED"
        purchase.received_at = datetime.utcnow()
        purchase.idempotency_key = request.idempotency_key # store the receive key
        
        db.flush()
        return {"synced": True, "movements": len(movements), "purchase_id": purchase.id}


    @staticmethod
    def record_payment(db: Session, purchase_id: int, request: PurchasePaymentRequest, operator_id: int) -> dict:
        purchase = db.query(Purchase).filter_by(id=purchase_id).first()
        if not purchase:
            raise ValueError("Purchase not found")
        
        if purchase.status != "RECEIVED":
            raise ValueError("Can only pay for RECEIVED purchases")
            
        amount_val = float(request.amount)
        
        # Update purchase
        current_paid = float(purchase.amount_paid or 0)
        purchase.amount_paid = current_paid + amount_val
        purchase.payment_method = request.method
        
        # Status logic
        if purchase.amount_paid >= purchase.total_amount:
            purchase.payment_status = "PAID"
        elif purchase.amount_paid > 0:
            purchase.payment_status = "PARTIAL"
        else:
            purchase.payment_status = "UNPAID"
            
        # Ledger entry
        vt = VendorTransaction(
            vendor_id=purchase.vendor_id,
            transaction_type='PAYMENT',
            amount=amount_val,
            ref_purchase_id=purchase.id,
            txn_ref=request.txn_ref,
            notes=request.notes
        )
        db.add(vt)
        
        # Deduct from vendor payable balance
        vendor = purchase.vendor
        vendor.payable_balance = float(vendor.payable_balance or 0) - amount_val
        
        db.flush()
        return {
            "purchase_id": purchase.id,
            "amount_paid": purchase.amount_paid,
            "payment_status": purchase.payment_status,
            "payable_balance": vendor.payable_balance
        }
