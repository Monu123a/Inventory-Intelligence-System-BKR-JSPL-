from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import shutil
import os
from datetime import datetime, timezone

from app.models.db import get_db
from app.models.schema import Inventory, InventoryMovement, Product
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.inventory_validation import InventoryValidationService
from app.services.inventory_adapter import InventoryAdapter
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/inventory", tags=["Inventory"])

class InventoryResponse(BaseModel):
    product_id: int
    company_id: int
    product_sku: str
    warehouse_id: int
    current_qty: int
    reserved_qty: int
    available_qty: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)

class MovementResponse(BaseModel):
    id: int
    company_id: int
    product_id: int
    timestamp: datetime
    product_sku: str
    warehouse_id: int
    qty_before: int
    qty_changed: int
    qty_after: int
    source: str
    reference_id: str
    metadata_payload: dict
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
def get_global_inventory_history(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """Inventory Timeline (History) for all products"""
    movements = db.query(InventoryMovement).options(joinedload(InventoryMovement.product)).filter(InventoryMovement.company_id == company_id).order_by(InventoryMovement.timestamp.desc()).all()
    
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
            "timestamp": mov.timestamp,
            "product_sku": mov.product_sku,
            "warehouse_id": mov.warehouse_id,
            "qty_before": mov.qty_before,
            "qty_changed": mov.qty_changed,
            "qty_after": mov.qty_after,
            "source": mov.source,
            "reference_id": mov.reference_id,
            "metadata_payload": payload,
            "display_metadata": disp_meta
        }
        result.append(mov_dict)
    
    return result

@router.get("/{sku}/history", response_model=List[MovementResponse])
def get_inventory_history(sku: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """Inventory Timeline (History) for a specific product"""
    product = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not product:
        return []
    return db.query(InventoryMovement).options(joinedload(InventoryMovement.product)).filter(
        InventoryMovement.company_id == company_id, 
        InventoryMovement.product_id == product.id
    ).order_by(InventoryMovement.timestamp.desc()).all()

@router.post("/upload")
async def upload_inventory(
    warehouse_code: str = Form(...),
    upload_type: str = Form(...), # "ADD" or "REPLACE"
    preview: bool = Form(False),
    file: UploadFile = File(...),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    if upload_type not in ["ADD", "REPLACE"]:
        raise HTTPException(status_code=400, detail="upload_type must be ADD or REPLACE")
    import tempfile
    import os
    import shutil
    from datetime import datetime, timezone
    
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
            
        reference_id = f"UPLOAD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Process via Event Engine
        try:
            for record in valid_records:
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=company_id,
                    product_sku=record["sku"],
                    warehouse_id=record["warehouse_id"],
                    quantity=record["quantity"],
                    event_type=upload_type,
                    source="Upload",
                    reference_id=reference_id,
                    metadata_payload={"filename": file.filename}
                )

            db.commit()
            return {"status": "success", "message": f"Processed {len(valid_records)} records successfully", "reference_id": reference_id}
        except Exception:
            db.rollback()
            raise
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

class ManualAdjustment(BaseModel):
    product_sku: str
    warehouse_id: int
    quantity: int
    adjustment_type: str # "INCREASE" or "DECREASE"
    reason: str
    reference_id: Optional[str] = None

@router.post("/adjust")
def adjust_inventory(adjustment: ManualAdjustment, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    if adjustment.adjustment_type not in ["INCREASE", "DECREASE"]:
        raise HTTPException(status_code=400, detail="adjustment_type must be INCREASE or DECREASE")
    
    qty = adjustment.quantity if adjustment.adjustment_type == "INCREASE" else -abs(adjustment.quantity)
    
    ref = adjustment.reference_id or f"MANUAL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    try:
        InventoryEventEngine.process_event(
            db=db,
            company_id=company_id,
            product_sku=adjustment.product_sku,
            warehouse_id=adjustment.warehouse_id,
            quantity=qty,
            event_type="ADD", # Delta adjustment
            source="Manual",
            reference_id=ref,
            metadata_payload={"reason": adjustment.reason}
        )
        db.commit()
        return {"status": "success", "message": "Manual adjustment successful", "reference_id": ref}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
