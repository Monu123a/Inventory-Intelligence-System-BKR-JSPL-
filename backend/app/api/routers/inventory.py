from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone

from app.models.db import get_db
from app.models.schema import Inventory, InventoryMovement, Product, User
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.inventory_validation import InventoryValidationService
from app.services.inventory_adapter import InventoryAdapter
from app.services.audit_log_service import AuditLogService
from app.api.dependencies import get_current_company_id, require_admin
from app.api.routers.auth import verify_admin_action_password
import os
import shutil
import tempfile
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])

class ProductInfo(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    item_rate: Optional[float] = 0.0
    min_stock_level: Optional[int] = 10
    model_config = ConfigDict(from_attributes=True)

class InventoryResponse(BaseModel):
    product_id: int
    company_id: int
    warehouse_id: int
    product: Optional[ProductInfo] = None
    current_qty: int
    reserved_qty: Optional[int] = 0
    available_qty: Optional[int] = 0
    last_updated: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class MovementResponse(BaseModel):
    id: int
    company_id: int
    product_id: int
    timestamp: datetime
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_id: int
    qty_before: int
    qty_changed: int
    qty_after: int
    source: Optional[str] = None
    reference_id: Optional[str] = None
    metadata_payload: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[InventoryResponse])
def get_inventory(warehouse_id: Optional[int] = None, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    query = db.query(Inventory).options(joinedload(Inventory.product)).filter(Inventory.company_id == company_id)
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    return query.all()

class GlobalMovementResponse(MovementResponse):
    display_metadata: List[dict]

@router.get("/history", response_model=List[GlobalMovementResponse])
def get_global_inventory_history(
    skip: int = 0,
    limit: int = 500,
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """Inventory Timeline (History) for all products"""
    movements = db.query(InventoryMovement).options(joinedload(InventoryMovement.product)).filter(InventoryMovement.company_id == company_id).order_by(InventoryMovement.timestamp.desc()).offset(skip).limit(min(limit, 2000)).all()
    
    result = []
    for mov in movements:
        disp_meta = []
        payload = mov.metadata_payload or {}
        
        # Format known metadata fields nicely
        for k, v in payload.items():
            label = k.replace("_", " ").title()
            disp_meta.append({"label": label, "value": str(v)})
            
        mov_dict = {
            "id": mov.id,
            "company_id": mov.company_id,
            "product_id": mov.product_id,
            "timestamp": mov.timestamp,
            "product_sku": mov.product.sku if mov.product else "Unknown",
            "product_name": mov.product.name if mov.product else "Unknown",
            "warehouse_id": mov.warehouse_id,
            "qty_before": mov.qty_before,
            "qty_changed": mov.qty_changed,
            "qty_after": mov.qty_after,
            "source": mov.source or "",
            "reference_id": mov.reference_id or "",
            "metadata_payload": payload,
            "display_metadata": disp_meta
        }
        result.append(mov_dict)
    
    return result

@router.get("/{sku}/history", response_model=List[GlobalMovementResponse])
def get_inventory_history(sku: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """Inventory Timeline (History) for a specific product"""
    product = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not product:
        return []
    movements = db.query(InventoryMovement).options(joinedload(InventoryMovement.product)).filter(
        InventoryMovement.company_id == company_id, 
        InventoryMovement.product_id == product.id
    ).order_by(InventoryMovement.timestamp.desc()).all()
    
    result = []
    for mov in movements:
        payload = mov.metadata_payload or {}
        disp_meta = [{"label": k.replace("_", " ").title(), "value": str(v)} for k, v in payload.items()]
        result.append({
            "id": mov.id,
            "company_id": mov.company_id,
            "product_id": mov.product_id,
            "timestamp": mov.timestamp,
            "product_sku": mov.product.sku if mov.product else "Unknown",
            "product_name": mov.product.name if mov.product else "Unknown",
            "warehouse_id": mov.warehouse_id,
            "qty_before": mov.qty_before,
            "qty_changed": mov.qty_changed,
            "qty_after": mov.qty_after,
            "source": mov.source or "",
            "reference_id": mov.reference_id or "",
            "metadata_payload": payload,
            "display_metadata": disp_meta
        })
    return result

@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_inventory(
    warehouse_code: str = Form(...),
    upload_type: str = Form(...), # "ADD" or "REPLACE"
    preview: bool = Form(False),
    admin_password: str = Form(None),
    file: UploadFile = File(...),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not preview:
        verify_admin_action_password(admin_password, current_user)
        
    if upload_type not in ["ADD", "REPLACE"]:
        raise HTTPException(status_code=400, detail="upload_type must be ADD or REPLACE")
    
    # Use a secure temp directory that works across platforms
    temp_dir = tempfile.gettempdir()
    # Sanitize the filename to prevent path traversal
    safe_filename = os.path.basename(file.filename)
    temp_file = os.path.join(temp_dir, f"inv_{datetime.now(timezone.utc).timestamp()}_{safe_filename}")
    
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Parse using Adapter
        parsed_records = InventoryAdapter.parse_inventory_file(temp_file)
        
        # Validate
        is_valid, valid_records, errors = InventoryValidationService.validate_upload(db, parsed_records, warehouse_code, company_id)
        
        if preview:
            return {
                "status": "preview",
                "is_valid": is_valid,
                "valid_records_count": len(valid_records),
                "total_parsed": len(parsed_records),
                "errors": errors
            }

        if not is_valid:
            return {"status": "error", "message": "Validation failed", "errors": errors}
            
        file_hash = hashlib.md5()
        with open(temp_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
        
        reference_id = f"UPLOAD-{file_hash.hexdigest()}"
        
        # Process via Event Engine
        try:
            for idx, record in enumerate(valid_records):
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=company_id,
                    product_sku=record["sku"],
                    warehouse_id=record["warehouse_id"],
                    quantity=record["quantity"],
                    event_type=upload_type,
                    source="Upload",
                    reference_id=reference_id,
                    metadata_payload={"filename": file.filename, "line_id": str(idx)}
                )

            db.commit()
            
            if not preview:
                logger.info({
                    "action": "UPLOAD_INVENTORY",
                    "user_id": current_user.id,
                    "company_id": company_id,
                    "warehouse_code": warehouse_code,
                    "upload_type": upload_type,
                    "records_processed": len(valid_records),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            return {"status": "success", "message": f"Processed {len(valid_records)} records successfully", "reference_id": reference_id}
        except Exception as e:
            logger.error(str(e), exc_info=True)
            db.rollback()
            raise
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

class ManualAdjustment(BaseModel):
    idempotency_key: Optional[str] = None
    product_sku: str
    warehouse_id: int
    quantity: int
    adjustment_type: str # "INCREASE" or "DECREASE"
    reason: str
    reference_id: Optional[str] = None
    admin_password: Optional[str] = Field(default=None, exclude=True)

@router.post("/adjust", dependencies=[Depends(require_admin)])
def adjust_inventory(adjustment: ManualAdjustment, company_id: int = Depends(get_current_company_id), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    verify_admin_action_password(adjustment.admin_password, current_user)
    
    if adjustment.adjustment_type not in ["INCREASE", "DECREASE"]:
        raise HTTPException(status_code=400, detail="adjustment_type must be INCREASE or DECREASE")
    
    if adjustment.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be a positive number")
    
    qty = abs(adjustment.quantity) if adjustment.adjustment_type == "INCREASE" else -abs(adjustment.quantity)
    
    ref = adjustment.reference_id or f"MANUAL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    metadata = {"reason": adjustment.reason}
    try:
        if adjustment.idempotency_key:
            metadata["operation_id"] = adjustment.idempotency_key

        InventoryEventEngine.process_event(
            db=db,
            company_id=company_id,
            product_sku=adjustment.product_sku,
            warehouse_id=adjustment.warehouse_id,
            quantity=abs(qty),
            event_type="ADD" if qty > 0 else "DEDUCT", # Delta adjustment
            source="Manual",
            reference_id=ref,
            metadata_payload=metadata
        )
            
        AuditLogService.log(
            db,
            company_id=company_id,
            entity_type="Inventory",
            entity_id=0,
            event_type="MANUAL_ADJUSTMENT",
            message=f"Manual inventory adjustment for {adjustment.product_sku} in warehouse {adjustment.warehouse_id}",
            metadata={"adjustment_type": adjustment.adjustment_type, "quantity": adjustment.quantity, "reason": adjustment.reason}
        )
        
        db.commit()
        
        logger.info({
            "action": "ADJUST_INVENTORY",
            "user_id": current_user.id,
            "company_id": company_id,
            "warehouse_id": adjustment.warehouse_id,
            "sku": adjustment.product_sku,
            "quantity": qty,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "success", "message": "Manual adjustment successful", "reference_id": ref}
    except IntegrityError:
        db.rollback()
        if adjustment.idempotency_key:
            existing = db.query(InventoryMovement).filter_by(
                operation_id=adjustment.idempotency_key,
                company_id=company_id
            ).first()
            if existing:
                return {"status": "success", "message": "Manual adjustment successful (Idempotent response)", "reference_id": ref}
        raise
    except ValueError as e:
        logger.error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        db.rollback()
        if e.status_code == 503 and adjustment.idempotency_key:
            existing = db.query(InventoryMovement).filter_by(
                operation_id=adjustment.idempotency_key,
                company_id=company_id
            ).first()
            if existing:
                return {"status": "success", "message": "Manual adjustment successful (Idempotent response)", "reference_id": ref}
        raise
    except Exception as e:
        logger.error(str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal error occurred during inventory adjustment.")
