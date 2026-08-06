from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from app.models.schema import FCReturn, FCReturnItem, FCDispatch, FCDispatchItem, Warehouse, Product
from app.services.inventory_event_engine import InventoryEventEngine
from pydantic import BaseModel

class FCReturnRequestItem(BaseModel):
    dispatch_item_id: int
    quantity: int
    return_reason: str = None

class FCReturnRequest(BaseModel):
    dispatch_id: int
    items: List[FCReturnRequestItem]

class FCReturnService:
    @staticmethod
    def _generate_return_number(db: Session, hub_code: str) -> str:
        count = db.query(FCReturn).count() + 1
        return f"WHR/{hub_code}/26-27/{count:05d}"

    @staticmethod
    def process_return(db: Session, company_id: int, request: FCReturnRequest, user_id: int):
        dispatch = db.query(FCDispatch).filter(FCDispatch.id == request.dispatch_id, FCDispatch.company_id == company_id).first()
        if not dispatch:
            raise HTTPException(status_code=404, detail="Dispatch not found")
            
        warehouse = db.query(Warehouse).filter(Warehouse.id == dispatch.warehouse_id).first()
        hub_code = warehouse.hub.hub_code if warehouse.hub else "FC"
        
        return_num = FCReturnService._generate_return_number(db, hub_code)
        fc_return = FCReturn(
            company_id=company_id,
            warehouse_id=dispatch.warehouse_id,
            dispatch_id=dispatch.id,
            return_number=return_num,
            status="Completed",
            created_by=user_id
        )
        db.add(fc_return)
        db.flush()
        
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
            from app.api.routers.pos import _resolve_default_bkr_warehouse
            default_warehouse = _resolve_default_bkr_warehouse(db, company_id)
            
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=dispatch_item.product.sku,
                warehouse_id=default_warehouse.id,
                quantity=req_item.quantity,
                event_type="TRANSFER_IN",
                source="FC_RETURN",
                reference_id=return_num,
                metadata_payload={"fc_return_id": fc_return.id}
            )
            
        db.commit()
        db.refresh(fc_return)
        return fc_return
