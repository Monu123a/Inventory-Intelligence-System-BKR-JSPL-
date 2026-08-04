from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.api.dependencies import get_current_user, get_db, get_current_company_id
from app.models.schema import User, StockTransfer
from app.services.stock_transfer_service import StockTransferService
from app.services.transfer_number_service import TransferNumberService
from sqlalchemy import func

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])

from pydantic import BaseModel
from typing import List, Optional

class TransferItemRequest(BaseModel):
    product_id: int
    requested_qty: int
    unit_price: Optional[float] = 0.0

class CreateTransferRequest(BaseModel):
    from_company_id: int
    to_company_id: int
    items: List[TransferItemRequest]

@router.post("/create")
def create_transfer(req: CreateTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    if req.from_company_id != company_id and req.to_company_id != company_id:
        raise HTTPException(status_code=403, detail="Cannot create transfer for unrelated companies")
        
    from app.models.schema import StockTransferItem
    transfer_num = TransferNumberService.generate_next(db, company_id=req.from_company_id)
    transfer = StockTransfer(
        transfer_number=transfer_num,
        from_company_id=req.from_company_id,
        to_company_id=req.to_company_id,
        status="Pending",
        created_by=current_user.id
    )
    db.add(transfer)
    db.flush()
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
        return {"status": "success", "transfer_id": transfer.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from pydantic import BaseModel
from app.models.schema import Inventory

class CompleteTransferRequest(BaseModel):
    invoice_id: int

@router.put("/{transfer_id}/complete")
def complete_transfer(transfer_id: int, req: CompleteTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), company_id: int = Depends(get_current_company_id)):
    try:
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer or (transfer.from_company_id != company_id and transfer.to_company_id != company_id):
            raise HTTPException(status_code=403, detail="Not authorized to complete this transfer")
            
        transfer = StockTransferService.complete_transfer(db, transfer_id, req.invoice_id, current_user.id)
        return {"status": "success", "transfer_id": transfer.id}
    except Exception as e:
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
from sqlalchemy import or_

@router.get("/")
def list_transfers(
    status: Optional[str] = None, 
    to_company_id: Optional[int] = None,
    history: Optional[bool] = False,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.schema import CompanySettings, Company
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
            "items": [{"product_id": i.product_id, "sku": i.product.sku} for i in t.items]
        })
        
    return result
