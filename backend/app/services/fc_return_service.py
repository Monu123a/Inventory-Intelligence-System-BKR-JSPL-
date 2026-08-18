from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.schema import FCReturn, FCReturnItem, FCDispatch, FCDispatchItem, Warehouse
from app.services.inventory_event_engine import InventoryEventEngine
from pydantic import BaseModel
from app.services.audit_log_service import AuditLogService
from app.api.routers.pos import _resolve_default_bkr_warehouse

class FCReturnRequestItem(BaseModel):
    dispatch_item_id: int
    quantity: int
    return_reason: Optional[str] = None

class FCReturnRequest(BaseModel):
    idempotency_key: Optional[str] = None
    dispatch_id: int
    items: List[FCReturnRequestItem]

class FCReturnService:
    @staticmethod
    def _generate_return_number(db: Session, company_id: int, hub_code: str) -> str:
        from datetime import date
        from app.services.document_number_service import DocumentNumberService
        from app.models.schema import DocumentTypeEnum
        
        d = date.today()
        start_year = d.year if d.month >= 4 else d.year - 1
        end_year = start_year + 1
        fy = f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"
        
        return DocumentNumberService.generate_number(
            db=db,
            company_id=company_id,
            document_type=DocumentTypeEnum.RETURN,
            fiscal_year=fy,
            prefix_override=f"WHR/{hub_code}"
        )

    @staticmethod
    def process_return(db: Session, company_id: int, request: FCReturnRequest, user_id: int):
        if request.idempotency_key:
            existing_return = db.query(FCReturn).filter_by(idempotency_key=request.idempotency_key, company_id=company_id).first()
            if existing_return:
                return existing_return
                
        dispatch = db.query(FCDispatch).filter(FCDispatch.id == request.dispatch_id, FCDispatch.company_id == company_id).first()
        if not dispatch:
            raise HTTPException(status_code=404, detail="Dispatch not found")
            
        warehouse = db.query(Warehouse).filter(Warehouse.id == dispatch.warehouse_id).first()
        hub_code = warehouse.hub.hub_code if warehouse.hub else "FC"
        
        return_num = FCReturnService._generate_return_number(db, company_id, hub_code)
        fc_return = FCReturn(
            company_id=company_id,
            warehouse_id=dispatch.warehouse_id,
            dispatch_id=dispatch.id,
            return_number=return_num,
            idempotency_key=request.idempotency_key,
            status="Completed",
            created_by=user_id
        )
        db.add(fc_return)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing_return = db.query(FCReturn).filter_by(idempotency_key=request.idempotency_key, company_id=company_id).first()
            if existing_return:
                return existing_return
            raise
        
        for req_item in request.items:
            dispatch_item = db.query(FCDispatchItem).filter(
                FCDispatchItem.id == req_item.dispatch_item_id,
                FCDispatchItem.dispatch_id == dispatch.id
            ).first()
            
            if not dispatch_item:
                raise HTTPException(status_code=404, detail=f"Dispatch Item {req_item.dispatch_item_id} not found in this dispatch")
                
            # Validate Returned Quantity <= Dispatched Quantity
            # Need to check total already returned for this dispatch_item
            already_returned = db.query(FCReturnItem).filter(FCReturnItem.dispatch_item_id == dispatch_item.id).all()
            total_returned_before = sum([r.quantity for r in already_returned])
            
            if total_returned_before + req_item.quantity > dispatch_item.quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot return {req_item.quantity} for item {dispatch_item.product.sku}. Only {dispatch_item.quantity - total_returned_before} remaining."
                )
                
            return_item = FCReturnItem(
                fc_return_id=fc_return.id,
                dispatch_item_id=dispatch_item.id,
                product_id=dispatch_item.product_id,
                quantity=req_item.quantity,
                return_reason=req_item.return_reason
            )
            db.add(return_item)
            
            # 1. Deduct from FC Warehouse
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=dispatch_item.product.sku,
                warehouse_id=dispatch.warehouse_id,
                quantity=req_item.quantity,
                event_type="TRANSFER_OUT",
                source="FC_RETURN",
                reference_id=return_num,
                metadata_payload={"fc_return_id": fc_return.id}
            )
            
            # 2. Add back to Main Warehouse (assuming default main warehouse for BKR)
            # Find the default BKR warehouse. If we don't have it easily available, we can query it.
            # Usually the source warehouse for dispatch is the Main Warehouse.
            # Let's get the default BKR warehouse.
            # Return stock to the ORIGINAL source warehouse, not a default
            source_warehouse_id = dispatch.source_warehouse_id
            if not source_warehouse_id:
                # Fallback to default only if source wasn't tracked
                source_warehouse_id = _resolve_default_bkr_warehouse(db, company_id).id
                
            print(f"[FC RETURN] Returning to warehouse: {source_warehouse_id}")
            
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=dispatch_item.product.sku,
                warehouse_id=source_warehouse_id,
                quantity=req_item.quantity,
                event_type="TRANSFER_IN",
                source="FC_RETURN",
                reference_id=return_num,
                metadata_payload={"fc_return_id": fc_return.id}
            )
            
        db.flush()
        
        AuditLogService.log(
            db,
            company_id=company_id,
            entity_type="FCReturn",
            entity_id=fc_return.id,
            event_type="FC_RETURN_PROCESSED",
            message=f"FC Return {return_num} processed for dispatch {dispatch.id}",
            metadata={"dispatch_id": dispatch.id, "items_count": len(request.items)}
        )
        
        db.refresh(fc_return)
        return fc_return
