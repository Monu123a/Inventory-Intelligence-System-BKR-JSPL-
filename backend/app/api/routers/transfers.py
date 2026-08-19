from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db, get_current_company_id
from app.models.schema import User, StockTransfer, StockTransferItem
from app.services.stock_transfer_service import StockTransferService
from app.services.transfer_number_service import TransferNumberService
from app.services.metrics_service import log_metric
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])

from pydantic import BaseModel
from typing import List, Optional

class TransferItemRequest(BaseModel):
    product_id: int
    requested_qty: int
    unit_price: Optional[float] = 0.0

class CreateTransferRequest(BaseModel):
    source_company_id: Optional[int] = None
    destination_company_id: Optional[int] = None
    from_company_id: Optional[int] = None  # Backward compatibility
    to_company_id: Optional[int] = None    # Backward compatibility
    source_warehouse_id: Optional[int] = None
    destination_warehouse_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    items: List[TransferItemRequest]

import os
from app.services.audit_log_service import AuditLogService

@router.post("/create")
def create_transfer(req: CreateTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    src_comp = req.source_company_id or req.from_company_id
    dest_comp = req.destination_company_id or req.to_company_id
    
    if src_comp != company_id and dest_comp != company_id:
        raise HTTPException(status_code=403, detail="Cannot create transfer for unrelated companies")
        
    is_cross_company = src_comp != dest_comp
    if is_cross_company:
        cross_enabled = os.getenv("CROSS_COMPANY_TRANSFERS", "false").lower() == "true"
        if not cross_enabled:
            raise HTTPException(status_code=403, detail="Cross company transfers are currently disabled")
            
        has_permission = current_user.role in ["Admin", "SuperAdmin"] or "create_transfer" in (current_user.permissions or []) or "cross_company_transfer" in (current_user.permissions or [])
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not authorized to create cross-company transfers")
        
    if req.idempotency_key:
        existing = db.query(StockTransfer).filter(
            StockTransfer.from_company_id == src_comp,
            StockTransfer.idempotency_key == req.idempotency_key
        ).first()
        if existing:
            return {"status": "success", "transfer_id": existing.id, "message": "Idempotent response"}

    transfer_num = TransferNumberService.generate_next(db, company_id=src_comp)
    transfer = StockTransfer(
        transfer_number=transfer_num,
        from_company_id=src_comp,
        to_company_id=dest_comp,
        source_warehouse_id=req.source_warehouse_id,
        destination_warehouse_id=req.destination_warehouse_id,
        idempotency_key=req.idempotency_key,
        status="Pending",
        created_by=current_user.id
    )
    db.add(transfer)
    db.flush()
    
    if is_cross_company:
        AuditLogService.log(
            db, 
            company_id=company_id, 
            entity_type="StockTransfer", 
            entity_id=transfer.id, 
            event_type="cross_company_transfer.create", 
            message="Created cross company transfer", 
            metadata={"source_company_id": src_comp, "destination_company_id": dest_comp},
            
        )

    for it in req.items:
        ti = StockTransferItem(
            transfer_id=transfer.id,
            product_id=it.product_id,
            requested_qty=it.requested_qty,
            unit_price=it.unit_price
        )
        db.add(ti)
    db.commit()
    return {"status": "success", "transfer_id": transfer.id}

@router.post("/{transfer_id}/approve")
def approve_transfer(transfer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    try:
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer or (transfer.from_company_id != company_id and transfer.to_company_id != company_id):
            raise HTTPException(status_code=403, detail="Not authorized to approve this transfer")
            
        transfer = StockTransferService.approve_transfer(db, transfer_id, current_user.id)
        db.commit()
        
        logger.info(f"Action: Transfer Approve | User: {current_user.id} | Company: {company_id} | Status: Success | TransferID: {transfer.id}")
        log_metric("transfer_approved", 1, {"company_id": company_id})
        
        return {"status": "success", "transfer_id": transfer.id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

from pydantic import BaseModel
from app.models.schema import Inventory

class CompleteTransferRequest(BaseModel):
    invoice_id: int
    idempotency_key: Optional[str] = None

@router.put("/{transfer_id}/complete")
def complete_transfer(transfer_id: int, req: CompleteTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    try:
        # Lock the row for concurrency
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).with_for_update().first()
        if not transfer or (transfer.from_company_id != company_id and transfer.to_company_id != company_id):
            raise HTTPException(status_code=403, detail="Not authorized to complete this transfer")
            
        if req.idempotency_key and transfer.idempotency_key != req.idempotency_key:
            raise HTTPException(status_code=400, detail="Idempotency key mismatch: Completion must use the same identity as creation.")
            
        if transfer.status == "Completed":
            return {"status": "success", "transfer_id": transfer.id, "message": "Already completed"}
            
        transfer = StockTransferService.complete_transfer_locked(db, transfer, req.invoice_id, current_user.id)
        db.commit()
        return {"status": "success", "transfer_id": transfer.id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{transfer_id}")
def get_transfer(transfer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
    if not transfer or (transfer.from_company_id != company_id and transfer.to_company_id != company_id):
        raise HTTPException(status_code=404, detail="Transfer not found")
        
    items = []
    for item in transfer.items:
        # Aggregate available stock across ALL warehouses for the source company
        total_available = db.query(
            func.sum(Inventory.available_qty)
        ).filter(
            Inventory.company_id == transfer.from_company_id,
            Inventory.product_id == item.product_id
        ).scalar() or 0
        
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "sku": item.product.sku if item.product else "",
            "product_sku": item.product.sku if item.product else "",
            "product_name": item.product.name if item.product else "",
            "product": item.product.name if item.product else "",
            "requested_qty": item.requested_qty,
            "unit_price": item.product.item_rate if item.product else 0,
            "available_qty": total_available
        })
        
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "from_company_id": transfer.from_company_id,
        "to_company_id": transfer.to_company_id,
        "items": items
    }

from typing import Optional
from app.models.schema import CompanySettings, Company
from app.models.schema import StockTransferItem

@router.get("/")
def list_transfers(
    status: Optional[str] = None, 
    to_company_id: Optional[int] = None,
    history: Optional[bool] = False,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(StockTransfer).filter(
        (StockTransfer.from_company_id == company_id) | 
        (StockTransfer.to_company_id == company_id)
    )
    
    if to_company_id:
        query = query.filter(StockTransfer.to_company_id == to_company_id)
        
    if history:
        query = query.filter(StockTransfer.status == "Completed")
    elif status == "active":
        query = query.filter(StockTransfer.status.in_(["Pending", "In Progress"]))
    elif status:
        query = query.filter(StockTransfer.status == status)
        
    query = query.order_by(StockTransfer.created_at.desc())
    transfers = query.all()
    
    # Pre-fetch companies for fast mapping
    companies_settings = {c.company_id: c.legal_name for c in db.query(CompanySettings).all()}
    companies_names = {c.id: c.name for c in db.query(Company).all()}
    
    result = []
    for t in transfers:
        total_qty = sum(item.requested_qty for item in t.items)
        total_amount = sum(item.requested_qty * item.unit_price for item in t.items)
        
        from_name = companies_settings.get(t.from_company_id) or companies_names.get(t.from_company_id) or "Unknown"
        to_name = companies_settings.get(t.to_company_id) or companies_names.get(t.to_company_id) or "Unknown"
        
        result.append({
            "id": t.id,
            "transfer_number": t.transfer_number,
            "status": t.status,
            "from_company_id": t.from_company_id,
            "to_company_id": t.to_company_id,
            "from_company_name": from_name,
            "to_company_name": to_name,
            "created_at": t.created_at,
            "invoice_id": t.invoice_id,
            "total_qty": total_qty,
            "total_amount": total_amount,
            "items_count": len(t.items),
            "items": [{"product_id": i.product_id, "sku": i.product.sku if i.product else "", "product_sku": i.product.sku if i.product else "", "product_name": i.product.name if i.product else ""} for i in t.items]
        })
        
    return result
