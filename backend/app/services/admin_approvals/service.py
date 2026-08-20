import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_
from app.models.schema import AdminApprovalRequest, AdminApprovalEvent, User
from app.services.admin_approvals.registry import ExecutorRegistry
from app.services.admin_approvals.executors import SnapshotMismatchError

class AdminApprovalService:
    @staticmethod
    def _check_feature_flag():
        if os.getenv("ENABLE_ADMIN_APPROVALS", "false").lower() != "true":
            raise ValueError("Admin approvals feature is currently disabled (ENABLE_ADMIN_APPROVALS=false)")

    @staticmethod
    def create_request(db: Session, request_type: str, payload: dict, requested_by: int, idempotency_key: str, company_id: int = None, related_entity: int = None):
        AdminApprovalService._check_feature_flag()
        executor = ExecutorRegistry.get(request_type)
        executor.validate(payload)

        user = db.query(User).filter(User.id == requested_by).first()
        user_role = user.role if user else None
        if user_role not in executor.allowed_request_roles:
            raise PermissionError(f"Role '{user_role}' is not allowed to request {request_type}")
        
        before_snapshot = executor.before_snapshot(db, payload)
        
        req = AdminApprovalRequest(
            request_type=request_type,
            payload=payload,
            requested_by=requested_by,
            company_id=company_id,
            related_entity=related_entity,
            idempotency_key=idempotency_key,
            before_snapshot=before_snapshot,
            status="PENDING"
        )
        db.add(req)
        
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Request with idempotency_key {idempotency_key} already exists.")
            
        event = AdminApprovalEvent(
            approval_request_id=req.id,
            event_type="CREATED",
            actor_id=requested_by,
            data={"before_snapshot": before_snapshot}
        )
        db.add(event)
        return req

    @staticmethod
    def approve_and_execute(db: Session, request_id: int, admin_id: int, idempotency_key: str, comment: str = None):
        AdminApprovalService._check_feature_flag()

        # Check DB-level execution idempotency to prevent cross-request race
        existing_exec = db.query(AdminApprovalRequest).filter(AdminApprovalRequest.execution_idempotency_key == idempotency_key).first()
        if existing_exec:
            if existing_exec.id == request_id and existing_exec.status == "EXECUTED":
                return {"status": "EXECUTED", "cached": True, "result": existing_exec.after_snapshot}
            raise ValueError(f"Execution idempotency_key {idempotency_key} was already used by another execution.")

        req = db.query(AdminApprovalRequest).filter(AdminApprovalRequest.id == request_id).with_for_update().first()
        if not req:
            raise ValueError("Request not found")
            
        if req.status == "EXECUTED":
            return {"status": "EXECUTED", "cached": True, "result": req.after_snapshot}
            
        if req.status not in ["PENDING", "APPROVED_PENDING_EXECUTION", "FAILED"]:
            raise ValueError(f"Cannot approve request in {req.status} state")

        executor = ExecutorRegistry.get(req.request_type)
        
        user = db.query(User).filter(User.id == admin_id).first()
        user_role = user.role if user else None
        if user_role not in executor.allowed_approve_roles:
            raise PermissionError(f"Role '{user_role}' is not allowed to approve {req.request_type}")

        # Try setting execution_idempotency_key immediately
        req.execution_idempotency_key = idempotency_key
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Race condition: Execution key {idempotency_key} already used.")

        executor.lock_entities(db, req.payload)
                
        current_snapshot = executor.before_snapshot(db, req.payload)
        executor.compare_snapshot(req.before_snapshot, current_snapshot)
            
        req.approver_id = admin_id
        req.approved_at = datetime.utcnow()
        if comment:
            req.admin_comment = comment

        req.status = "APPROVED_PENDING_EXECUTION"
        db.add(AdminApprovalEvent(approval_request_id=req.id, event_type="APPROVED", actor_id=admin_id, data={}))
        db.flush()

        req.status = "EXECUTING"
        db.add(AdminApprovalEvent(approval_request_id=req.id, event_type="EXECUTING", actor_id=admin_id, data={}))
        db.flush()
        
        try:
            result = executor.execute(db, req.payload, idempotency_key)
            req.after_snapshot = result
            req.revert_payload = executor.reverse_payload(req.payload, req.before_snapshot)
            req.status = "EXECUTED"
            
            db.add(AdminApprovalEvent(
                approval_request_id=req.id,
                event_type="EXECUTED",
                actor_id=admin_id,
                data=result
            ))
            return {"status": "EXECUTED", "result": result}
            
        except Exception as e:
            req.status = "FAILED"
            db.add(AdminApprovalEvent(
                approval_request_id=req.id,
                event_type="FAILED",
                actor_id=admin_id,
                data={"error": str(e)}
            ))
            raise e

    @staticmethod
    def cleanup_stuck_requests(db: Session, timeout_minutes: int = 5):
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stuck_requests = db.query(AdminApprovalRequest).filter(
            AdminApprovalRequest.status == "EXECUTING",
            AdminApprovalRequest.updated_at < timeout_threshold
        ).all()

        count = 0
        for req in stuck_requests:
            req.status = "FAILED"
            db.add(AdminApprovalEvent(
                approval_request_id=req.id,
                event_type="FAILED_TIMEOUT",
                actor_id=None,
                data={"error": f"Stuck in EXECUTING for > {timeout_minutes} mins"}
            ))
            count += 1
        db.commit()
        return count

    @staticmethod
    def revert_request(db: Session, request_id: int, admin_id: int):
        req = db.query(AdminApprovalRequest).filter(AdminApprovalRequest.id == request_id).with_for_update().first()
        if not req or req.status != "EXECUTED":
            raise ValueError("Only EXECUTED requests can be reverted.")

        executor = ExecutorRegistry.get(req.request_type)
        
        user = db.query(User).filter(User.id == admin_id).first()
        user_role = user.role if user else None
        if user_role not in executor.allowed_approve_roles:
            raise PermissionError("Only approvers can revert actions.")
            
        executor.lock_entities(db, req.revert_payload)
        
        # Verify snapshot before revert (Ensure no one changed it after execution)
        current_snapshot = executor.before_snapshot(db, req.revert_payload)
        
        # We need to construct expected current snapshot from 'after_snapshot' to compare strictly
        # We enforce strict checking:
        if req.after_snapshot.get('price') != current_snapshot.get('price'):
             raise ValueError("Data has changed since execution. Unsafe to revert.")
        
        result = executor.execute(db, req.revert_payload, f"revert-{req.execution_idempotency_key or req.idempotency_key}")
        
        req.status = "REVERTED"
        db.add(AdminApprovalEvent(
            approval_request_id=req.id,
            event_type="REVERTED",
            actor_id=admin_id,
            data={"revert_result": result}
        ))
        db.flush()
        return {"status": "REVERTED", "result": result}
