import json
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.models.db import get_db
from app.models.schema import User, AdminApprovalRequest
from app.services.admin_approvals.service import AdminApprovalService
from app.services.admin_approvals.executors import SnapshotMismatchError

router = APIRouter()

def get_payload_hash(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()

class CreateRequestPayload(BaseModel):
    request_type: str
    payload: Dict[str, Any]
    idempotency_key: str
    company_id: Optional[int] = None
    related_entity: Optional[int] = None

class ApproveRequestPayload(BaseModel):
    idempotency_key: str
    comment: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_approval_request(
    data: CreateRequestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # API Level Guard: Role basic check (Service layer does strict check too)
        if current_user.role not in ["Admin", "Manager", "Operator"]:
            raise HTTPException(status_code=403, detail="Not allowed to create requests")

        # 1. API Level Idempotency Protection
        existing = db.query(AdminApprovalRequest).filter(
            AdminApprovalRequest.idempotency_key == data.idempotency_key
        ).first()
        if existing:
            return {"message": "Request already exists", "request_id": existing.id, "cached": True}

        # 2. Rate Limiting: Max 20 pending requests per user
        pending_count = db.query(AdminApprovalRequest).filter(
            AdminApprovalRequest.requested_by == current_user.id,
            AdminApprovalRequest.status == "PENDING"
        ).count()
        if pending_count >= 20:
            raise HTTPException(status_code=429, detail="Too many pending requests. Please wait for admins to review.")

        # 3. Deduplication via Hash
        p_hash = get_payload_hash(data.payload)
        duplicate = db.query(AdminApprovalRequest).filter(
            AdminApprovalRequest.request_type == data.request_type,
            AdminApprovalRequest.status == "PENDING",
            AdminApprovalRequest.payload_hash == p_hash
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="An identical request is already pending approval.")

        req = AdminApprovalService.create_request(
            db=db,
            request_type=data.request_type,
            payload=data.payload,
            requested_by=current_user.id,
            idempotency_key=data.idempotency_key,
            company_id=data.company_id,
            related_entity=data.related_entity
        )
        
        req.payload_hash = p_hash
        req.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2) # 48 hr expiry
        
        db.commit()
        return {"message": "Request created successfully", "request_id": req.id}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{request_id}/approve")
def approve_request(
    request_id: int,
    data: ApproveRequestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # API Level Guards
        if current_user.role != "Admin":
            raise HTTPException(status_code=403, detail="Admin only")
            
        req = db.query(AdminApprovalRequest).filter(AdminApprovalRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.status == "EXECUTED":
             return {"status": "EXECUTED", "cached": True, "result": req.after_snapshot}
        if req.status != "PENDING":
            raise HTTPException(status_code=400, detail="Request is not in PENDING state")
        if req.expires_at and req.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            req.status = "EXPIRED"
            db.commit()
            raise HTTPException(status_code=400, detail="Request has expired")

        res = AdminApprovalService.approve_and_execute(
            db=db,
            request_id=request_id,
            admin_id=current_user.id,
            idempotency_key=data.idempotency_key,
            comment=data.comment
        )
        db.commit()
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SnapshotMismatchError as e:
        raise HTTPException(status_code=409, detail={"reason": "snapshot_mismatch", "diff": e.diff})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{request_id}/cancel")
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(AdminApprovalRequest).filter(
        AdminApprovalRequest.id == request_id,
        AdminApprovalRequest.requested_by == current_user.id
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found or not owned by you.")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING requests can be canceled.")
        
    req.status = "CANCELED"
    req.admin_comment = "Canceled by requester."
    db.commit()
    return {"message": "Request canceled successfully."}

@router.post("/{request_id}/revert")
def revert_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role != "Admin":
            raise HTTPException(status_code=403, detail="Admin only")
            
        res = AdminApprovalService.revert_request(db=db, request_id=request_id, admin_id=current_user.id)
        db.commit()
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def list_requests(
    response: Response,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AdminApprovalRequest)
    if current_user.role != "Admin":
        query = query.filter(AdminApprovalRequest.requested_by == current_user.id)
    if status:
        query = query.filter(AdminApprovalRequest.status == status)
        
    total = query.count()
    response.headers["X-Total-Count"] = str(total)
    return query.order_by(AdminApprovalRequest.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{request_id}/preview")
def preview_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(AdminApprovalRequest).filter(AdminApprovalRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    try:
        from app.services.admin_approvals.registry import ExecutorRegistry
        executor = ExecutorRegistry.get(req.request_type)
        preview_data = executor.dry_run(db, req.payload)
        
        return {
            "request_id": req.id, 
            "preview": preview_data,
            "original_snapshot": req.before_snapshot,
            "current_snapshot": executor.before_snapshot(db, req.payload),
            "request_reason": req.payload.get("_reason", "No reason provided.") if req.payload else "No reason provided."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview failed: {str(e)}")

class VerifyPasswordPayload(BaseModel):
    password: str

@router.post("/verify-password")
def verify_dashboard_password(
    data: VerifyPasswordPayload,
    current_user: User = Depends(get_current_user)
):
    from app.api.routers.auth import verify_admin_action_password
    verify_admin_action_password(data.password, current_user)
    return {"status": "ok"}
