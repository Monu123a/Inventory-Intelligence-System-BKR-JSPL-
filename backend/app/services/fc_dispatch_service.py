from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from app.models.schema import FCDispatch, FCDispatchItem, StateHub, Warehouse, Product, Sale, DeliveryChallan, CompanySettings
from app.api.routers.pos import complete_sale, PosCheckoutRequest, PosCartItem
from app.services.delivery_challan_service import DeliveryChallanService, CreateDeliveryChallanRequest, CreateDeliveryChallanItemRequest
from app.services.inventory_engine import InventoryEventEngine
from pydantic import BaseModel

class FCDispatchRequestItem(BaseModel):
    product_id: int
    quantity: int

class FCDispatchBatchRequest(BaseModel):
    warehouse_ids: List[int]
    items: List[FCDispatchRequestItem]

class FCDispatchService:
    @staticmethod
    def _generate_dispatch_number(db: Session, hub_code: str) -> str:
        count = db.query(FCDispatch).count() + 1
        return f"WHT/{hub_code}/26-27/{count:05d}"

    @staticmethod
    def create_batch_dispatch(db: Session, company_id: int, request: FCDispatchBatchRequest, user_id: int):
        dispatches = []
        for warehouse_id in request.warehouse_ids:
            # 1. Fetch FC Details
            warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.company_id == company_id).first()
            if not warehouse:
                raise HTTPException(status_code=404, detail=f"Warehouse {warehouse_id} not found")
            
            hub = db.query(StateHub).filter(StateHub.id == warehouse.hub_id).first()
            if not hub:
                raise HTTPException(status_code=400, detail=f"Warehouse {warehouse.name} has no associated State Hub")
            
            if not hub.gstin:
                raise HTTPException(status_code=400, detail=f"State Hub {hub.hub_name} missing GSTIN")
                
            # 2. Prepare POS Request
            pos_items = []
            taxable_total = 0.0
            tax_total = 0.0
            
            for req_item in request.items:
                product = db.query(Product).filter(Product.id == req_item.product_id).first()
                if not product:
                    raise HTTPException(status_code=404, detail=f"Product {req_item.product_id} not found")
                
                qty = req_item.quantity
                unit_price = product.item_rate or 0.0
                gst_rate = product.default_gst_rate or 0.0
                
                taxable = qty * unit_price
                gst = taxable * (gst_rate / 100.0)
                line_total = taxable + gst
                
                taxable_total += taxable
                tax_total += gst
                
                pos_items.append(PosCartItem(
                    product_id=product.id,
                    sku=product.sku,
                    product_name=product.name,
                    hsn_sac=product.hsn_code,
                    unit=product.unit,
                    quantity=qty,
                    selling_price=unit_price,
                    discount=0.0,
                    gst_rate=gst_rate,
                    taxable_amount=taxable,
                    cgst=gst/2,
                    sgst=gst/2,
                    igst=0.0,
                    line_total=line_total
                ))
            
            pos_request = PosCheckoutRequest(
                customer_name=hub.hub_name,
                customer_gstin=hub.gstin,
                customer_address=warehouse.address or hub.address,
                customer_state=hub.state,
                customer_state_code=hub.state_code,
                invoice_type="B2B",
                payment_method="CASH", # Default
                total_taxable_amount=taxable_total,
                total_tax=tax_total,
                grand_total=taxable_total + tax_total,
                items=pos_items
            )
            
            # 3. Call pos.py complete_sale
            sale_dto = complete_sale(request=pos_request, company_id=company_id, db=db)
            sale_id = sale_dto["id"]
            sale_obj = db.query(Sale).filter(Sale.id == sale_id).first()
            
            # 4. Create FCDispatch Orchestrator
            dispatch_num = FCDispatchService._generate_dispatch_number(db, hub.hub_code)
            
            dispatch_status = "Completed"
            if sale_obj.tally_sync_status in ["PENDING", "PROCESSING"]:
                dispatch_status = "XML Pending"
            elif sale_obj.tally_sync_status == "FAILED":
                dispatch_status = "Completed with Errors"
                
            dispatch = FCDispatch(
                company_id=company_id,
                warehouse_id=warehouse.id,
                invoice_id=sale_id,
                dispatch_number=dispatch_num,
                dispatch_status=dispatch_status,
                created_by=user_id
            )
            db.add(dispatch)
            db.flush()
            
            # 5. Create Challan
            challan_req = CreateDeliveryChallanRequest(
                sale_id=sale_id,
                dispatch_document_number=dispatch_num,
                destination=warehouse.name,
                items=[CreateDeliveryChallanItemRequest(
                    product_id=it.product_id,
                    quantity=it.quantity,
                    remarks="FC Dispatch"
                ) for it in pos_items]
            )
            challan_dto = DeliveryChallanService.create_challan(db, company_id, challan_req, user_id)
            dispatch.delivery_challan_id = challan_dto.id
            
            # 6. Increase Inventory at FC Warehouse
            for it in pos_items:
                di = FCDispatchItem(
                    dispatch_id=dispatch.id,
                    product_id=it.product_id,
                    sku_snapshot=it.sku,
                    product_name_snapshot=it.product_name,
                    hsn_snapshot=it.hsn_sac,
                    quantity=it.quantity,
                    unit_price=it.selling_price,
                    gst_rate=it.gst_rate,
                    taxable_amount=it.taxable_amount,
                    tax_amount=it.cgst + it.sgst + it.igst,
                    total_amount=it.line_total
                )
                db.add(di)
                
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=company_id,
                    product_sku=it.sku,
                    warehouse_id=warehouse.id,
                    quantity=it.quantity,
                    event_type="TRANSFER_IN",
                    source="FC_DISPATCH",
                    reference_id=dispatch_num,
                    metadata_payload={"dispatch_id": dispatch.id}
                )
            
            db.commit()
            db.refresh(dispatch)
            dispatches.append(dispatch)
            
        return dispatches
