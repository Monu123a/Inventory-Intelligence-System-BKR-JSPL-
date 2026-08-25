from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.models.db import get_db
from app.models.schema import User, Purchase, OfflinePurchase, Vendor
from app.api.routers.auth import get_current_user
from app.services.purchase_service import PurchaseService, PurchaseDraftRequest, PurchaseReceiveRequest
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchases", tags=["Purchases"])

def require_admin_or_manager(user: User = Depends(get_current_user)):
    if not user.role or user.role.upper() not in ["ADMIN", "MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Requires ADMIN or MANAGER role to execute Stock In / Receive"
        )
    return user

@router.post("/", summary="Create Purchase Draft")
def create_purchase_draft(
    request: PurchaseDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        res = PurchaseService.create_draft(db, request, user.id)
        db.commit()
        return res
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("Error creating purchase draft")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{purchase_id}/receive", summary="Receive Purchase Stock")
def receive_purchase(
    purchase_id: int,
    request: PurchaseReceiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_manager) # ENFORCED
):
    try:
        res = PurchaseService.receive_purchase(db, purchase_id, request, user.id)
        db.commit()
        return res
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("Error receiving purchase")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class OfflinePurchaseRequest(PurchaseDraftRequest):
    pass # Inherits structure

@router.post("/offline/submit", summary="Queue Offline Purchase")
def submit_offline_purchase(
    request: OfflinePurchaseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        existing = db.query(OfflinePurchase).filter_by(company_id=request.company_id, idempotency_key=request.idempotency_key).first()
        if existing:
            return {"status": "PENDING", "message": "Already queued"}

        offline_rec = OfflinePurchase(
            company_id=request.company_id,
            operator_id=user.id,
            payload=request.model_dump(),
            idempotency_key=request.idempotency_key
        )
        db.add(offline_rec)
        db.commit()
        return {"status": "PENDING", "id": offline_rec.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error queueing offline purchase")

@router.post("/offline/sync", summary="Sync Offline Purchases")
def sync_offline_purchases(
    company_id: int,
    db: Session = Depends(get_db)
):
    pendings = db.query(OfflinePurchase).filter_by(company_id=company_id, status="PENDING").all()
    results = []
    
    for op in pendings:
        try:
            req_data = PurchaseDraftRequest(**op.payload)
            # Find the user manually since this is a server sync loop
            # the operator_id is inside the OfflinePurchase row
            res = PurchaseService.create_draft(db, req_data, op.operator_id)
            
            op.status = "SYNCED"
            op.purchase_id = res['id']
            results.append({"idempotency_key": op.idempotency_key, "synced": True, "purchase_id": op.purchase_id})
        except Exception as e:
            op.status = "FAILED"
            op.error_message = str(e)
            results.append({"idempotency_key": op.idempotency_key, "synced": False, "error": str(e)})
            
    db.commit()
    return {"synced": len(results), "details": results}

@router.get("/vendors/payables", summary="Get Vendor Payables")
def get_vendor_payables(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vendors = db.query(Vendor).filter_by(company_id=company_id).all()
    return [{"id": v.id, "name": v.name, "payable_balance": v.payable_balance} for v in vendors]
