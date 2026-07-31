from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.api.dependencies import get_current_user, get_db
from app.models.schema import User, StockTransfer
from app.services.stock_transfer_service import StockTransferService
from app.services.transfer_number_service import TransferNumberService

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])

@router.post("/create")
def create_transfer(company_id: int, to_company_id: int, items: list, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.schema import StockTransferItem
    transfer_num = TransferNumberService.generate_next(db, company_id=company_id)
    transfer = StockTransfer(
        transfer_number=transfer_num,
        from_company_id=company_id,
        to_company_id=to_company_id,
        status="Pending",
        created_by=current_user.id
    )
    db.add(transfer)
    db.flush()
    for it in items:
        ti = StockTransferItem(
            transfer_id=transfer.id,
            product_id=it['product_id'],
            requested_qty=it['requested_qty'],
            unit_price=it.get('unit_price', 0.0)
        )
        db.add(ti)
    db.commit()
    return {"status": "success", "transfer_id": transfer.id}

@router.post("/{transfer_id}/approve")
def approve_transfer(transfer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        transfer = StockTransferService.approve_transfer(db, transfer_id, current_user.id)
        return {"status": "success", "transfer_id": transfer.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from pydantic import BaseModel
from app.models.schema import Inventory

class CompleteTransferRequest(BaseModel):
    invoice_id: int

@router.put("/{transfer_id}/complete")
def complete_transfer(transfer_id: int, req: CompleteTransferRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        transfer = StockTransferService.complete_transfer(db, transfer_id, req.invoice_id, current_user.id)
        return {"status": "success", "transfer_id": transfer.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{transfer_id}")
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
        
    items = []
    for item in transfer.items:
        source_inv = db.query(Inventory).filter(
            Inventory.company_id == transfer.from_company_id,
            Inventory.product_id == item.product_id
        ).first()
        available_qty = source_inv.current_qty if source_inv else 0
        
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "requested_qty": item.requested_qty,
            "unit_price": item.unit_price,
            "available_qty": available_qty
        })
        
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "from_company_id": transfer.from_company_id,
        "to_company_id": transfer.to_company_id,
        "items": items
    }
