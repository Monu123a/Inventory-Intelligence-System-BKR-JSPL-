from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import logging
from app.models.schema import (
    FCDispatch, FCDispatchItem, StateHub, Warehouse, Product, Sale, 
    DeliveryChallan, CompanySettings, DispatchTimeline, WarehouseStatus, Inventory, AuditLog
)
from app.api.routers.pos import complete_sale, PosCheckoutRequest, PosCartItem
from app.services.delivery_challan_service import DeliveryChallanService
from app.services.inventory_event_engine import InventoryEventEngine
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FCDispatchRequestItem(BaseModel):
    product_id: int
    quantity: int

class FCDispatchBatchRequest(BaseModel):
    source_type: str = "BKR" # BKR or CENTRAL_WAREHOUSE
    source_warehouse_id: Optional[int] = None
    warehouse_ids: List[int] # Dest FCs
    hub_id: Optional[int] = None # Optional manual override from frontend
    items: List[FCDispatchRequestItem]

class FCDispatchService:
    @staticmethod
    def _generate_dispatch_number(db: Session, hub_code: str) -> str:
        count = db.query(FCDispatch).count() + 1
        return f"WHT/{hub_code}/26-27/{count:05d}"

    @staticmethod
    def _log_timeline(db: Session, dispatch_id: int, step: str, status: str, user_id: int, remarks: str = None):
        timeline = DispatchTimeline(
            dispatch_id=dispatch_id,
            step=step,
            status=status,
            performed_by=user_id,
            remarks=remarks
        )
        db.add(timeline)
        db.flush()
        
    @staticmethod
    def _log_audit(db: Session, company_id: int, user_id: int, action: str, entity_type: str, entity_id: int, message: str, payload: dict = None):
        if payload is None:
            payload = {}
        payload["user_id"] = user_id
        
        log = AuditLog(
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=action,
            message=message,
            metadata_payload=payload
        )
        db.add(log)
        db.flush()

    @staticmethod
    def create_batch_dispatch(db: Session, company_id: int, request: FCDispatchBatchRequest, user_id: int):
        dispatches = []
        try:
            # 1. Resolve Source Warehouse
            if request.source_type == "BKR":
                if request.source_warehouse_id:
                    source_warehouse = db.query(Warehouse).filter(
                        Warehouse.id == request.source_warehouse_id
                    ).first()
                else:
                    # Dynamically resolve BKR warehouse (usually company 2)
                    source_warehouse = db.query(Warehouse).filter(
                        Warehouse.name.ilike("%BKR%")
                    ).first()
                    
                if not source_warehouse:
                    raise HTTPException(status_code=404, detail="Source Warehouse not found")
                transaction_origin = "FC_DISPATCH"
            elif request.source_type == "CENTRAL_WAREHOUSE":
                source_warehouse = db.query(Warehouse).filter(
                    Warehouse.company_id == company_id,
                    Warehouse.warehouse_type == "FULFILLMENT_CENTER" # Temp workaround till enum update
                ).first()
                # Overwrite if we have CENTRAL properly typed (SQLite enum weirdness)
                central = db.query(Warehouse).filter(
                    Warehouse.company_id == company_id,
                    Warehouse.warehouse_type == "CENTRAL"
                ).first()
                if central:
                    source_warehouse = central
                elif not source_warehouse:
                    # ultimate fallback for test environments without correct type
                    source_warehouse = db.query(Warehouse).filter(
                        Warehouse.company_id == company_id
                    ).first()

                if not source_warehouse:
                    raise HTTPException(status_code=404, detail="No Central Warehouse found for this company")
                transaction_origin = "INTERNAL_DISTRIBUTION"
            else:
                raise HTTPException(status_code=400, detail=f"Invalid source_type {request.source_type}")

            if source_warehouse.status != WarehouseStatus.ACTIVE:
                raise HTTPException(status_code=400, detail=f"Source Warehouse must be ACTIVE (currently {source_warehouse.status})")

            company_settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
            export_to_accounting = True
            if request.source_type == "CENTRAL_WAREHOUSE" and company_settings:
                export_to_accounting = company_settings.export_internal_distribution_to_accounting

            for dest_warehouse_id in request.warehouse_ids:
                if dest_warehouse_id == source_warehouse.id:
                    raise HTTPException(status_code=400, detail="Source and destination warehouses cannot be the same")

                # 2. Fetch Dest FC Details
                dest_warehouse = db.query(Warehouse).filter(Warehouse.id == dest_warehouse_id).first()
                if not dest_warehouse:
                    raise HTTPException(status_code=404, detail=f"Destination Warehouse {dest_warehouse_id} not found")
                
                # Cross-company validation
                if request.source_type == "CENTRAL_WAREHOUSE" and dest_warehouse.company_id != company_id:
                    raise HTTPException(status_code=400, detail="Destination warehouse belongs to a different company")

                if dest_warehouse.status != WarehouseStatus.ACTIVE:
                    raise HTTPException(status_code=400, detail=f"Destination Warehouse {dest_warehouse.name} is not ACTIVE")

                hub_id = dest_warehouse.hub_id or request.hub_id
                if not hub_id:
                    raise HTTPException(status_code=400, detail=f"Destination Warehouse {dest_warehouse.name} lacks a State Hub (Migration Required)")
                
                hub = db.query(StateHub).filter(StateHub.id == hub_id).first()
                if not hub:
                    raise HTTPException(status_code=400, detail=f"Fulfillment Center {dest_warehouse.name} is missing a valid State Hub")
                    
                if hub.status != "Active":
                    raise HTTPException(status_code=400, detail=f"State Hub {hub.hub_name} is not Active")
                    
                # 3. Prepare POS Request & Validate Inventory
                pos_items = []
                taxable_total = 0.0
                tax_total = 0.0
                
                for req_item in request.items:
                    if req_item.quantity <= 0:
                        raise HTTPException(status_code=400, detail="Transfer quantity must be greater than zero")

                    product = db.query(Product).filter(Product.id == req_item.product_id).first()
                    if not product:
                        raise HTTPException(status_code=404, detail=f"Product {req_item.product_id} not found")
                    
                    # Validate Source Inventory
                    inventory = db.query(Inventory).filter(
                        Inventory.company_id == source_warehouse.company_id,
                        Inventory.warehouse_id == source_warehouse.id,
                        Inventory.product_id == product.id
                    ).first()
                    
                    avail_qty = inventory.available_qty if inventory else 0
                    if req_item.quantity > avail_qty:
                        raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name} at source warehouse. Needed {req_item.quantity}, available {avail_qty}")
                    
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
                    customer_address=hub.address,
                    customer_state=hub.state,
                    customer_state_code=hub.state_code,
                    invoice_type="B2B",
                    payment_method="CASH", # Default
                    total_taxable_amount=taxable_total,
                    total_tax=tax_total,
                    grand_total=taxable_total + tax_total,
                    origin_warehouse_id=source_warehouse.id,
                    skip_inventory_update=True,
                    items=pos_items
                )
                
                # Create FCDispatch Orchestrator
                dispatch_num = FCDispatchService._generate_dispatch_number(db, hub.hub_code)
                dispatch = FCDispatch(
                    company_id=company_id,
                    source_warehouse_id=source_warehouse.id,
                    warehouse_id=dest_warehouse.id,
                    dispatch_number=dispatch_num,
                    dispatch_status="Processing",
                    created_by=user_id
                )
                db.add(dispatch)
                db.flush()
                FCDispatchService._log_timeline(db, dispatch.id, "Created", "Success", user_id, f"Dispatch {dispatch_num} initiated from {source_warehouse.name}")
                FCDispatchService._log_audit(db, company_id, user_id, "CREATE", "FCDispatch", dispatch.id, f"Dispatch {dispatch_num} Created")

                # 4. Call pos.py complete_sale (with commit=False)
                sale_dto = complete_sale(request=pos_request, company_id=company_id, db=db, commit=False)
                sale_id = sale_dto["receipt"]["id"]
                sale_obj = db.query(Sale).filter(Sale.id == sale_id).first()
                sale_obj.transaction_origin = transaction_origin
                dispatch.invoice_id = sale_id
                
                # Prevent accounting export if disabled for internal dist
                if not export_to_accounting:
                    sale_obj.tally_sync_status = "SKIPPED"
                
                db.flush()
                FCDispatchService._log_timeline(db, dispatch.id, "Invoice Generated", "Success", user_id, f"Invoice ID {sale_id}")
                
                # 5. Create Challan
                challan_data = {
                    "sale_id": sale_id,
                    "challan_number": dispatch_num,
                    "remarks": f"{request.source_type} Dispatch",
                    "shipping_snapshot": {
                        "name": dest_warehouse.name,
                        "address": dest_warehouse.address,
                        "state": dest_warehouse.state,
                        "state_code": dest_warehouse.state_code,
                        "gstin": hub.gstin # Usually same GSTIN for same state
                    },
                    "items": [{
                        "product_id": it.product_id,
                        "quantity": it.quantity
                    } for it in pos_items]
                }
                challan_dto = DeliveryChallanService.create_challan(db, company_id, challan_data, user_id)
                dispatch.delivery_challan_id = challan_dto.id
                db.flush()
                FCDispatchService._log_timeline(db, dispatch.id, "Challan Generated", "Success", user_id, f"Challan ID {challan_dto.id}")
                
                # 6. Process Inventory
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
                    
                    # Deduct from Source
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=company_id,
                        product_sku=it.sku,
                        warehouse_id=source_warehouse.id,
                        quantity=it.quantity,
                        event_type="TRANSFER_OUT",
                        source="FC_DISPATCH_OUT",
                        reference_id=dispatch_num,
                        metadata_payload={"dispatch_id": dispatch.id}
                    )
                    
                    # Add to Dest FC
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=company_id,
                        product_sku=it.sku,
                        warehouse_id=dest_warehouse.id,
                        quantity=it.quantity,
                        event_type="TRANSFER_IN",
                        source="FC_DISPATCH_IN",
                        reference_id=dispatch_num,
                        metadata_payload={"dispatch_id": dispatch.id}
                    )
                db.flush()
                FCDispatchService._log_timeline(db, dispatch.id, "Inventory Updated", "Success", user_id, "Stock transferred")
                
                # Update final status based on XML sync status
                if sale_obj.tally_sync_status in ["PENDING", "PROCESSING"]:
                    dispatch.dispatch_status = "XML Pending"
                    FCDispatchService._log_timeline(db, dispatch.id, "XML Queued", "Pending", user_id)
                    FCDispatchService._log_audit(db, company_id, user_id, "XML_QUEUED", "FCDispatch", dispatch.id, f"Invoice {sale_id} queued for Tally")
                elif sale_obj.tally_sync_status == "SKIPPED":
                    dispatch.dispatch_status = "Completed"
                    FCDispatchService._log_timeline(db, dispatch.id, "XML Skipped", "Skipped", user_id, "Configuration Disabled")
                    FCDispatchService._log_audit(db, company_id, user_id, "XML_SKIPPED", "FCDispatch", dispatch.id, f"Invoice {sale_id} XML skipped")
                    FCDispatchService._log_timeline(db, dispatch.id, "Completed", "Success", user_id)
                    FCDispatchService._log_audit(db, company_id, user_id, "COMPLETE", "FCDispatch", dispatch.id, f"Dispatch {dispatch_num} Completed")
                elif sale_obj.tally_sync_status == "FAILED":
                    dispatch.dispatch_status = "Completed with Errors"
                    FCDispatchService._log_timeline(db, dispatch.id, "XML Queued", "Failed", user_id)
                    FCDispatchService._log_audit(db, company_id, user_id, "XML_FAILED", "FCDispatch", dispatch.id, f"Invoice {sale_id} XML failed")
                else:
                    dispatch.dispatch_status = "Completed"
                    FCDispatchService._log_timeline(db, dispatch.id, "Completed", "Success", user_id)
                    FCDispatchService._log_audit(db, company_id, user_id, "COMPLETE", "FCDispatch", dispatch.id, f"Dispatch {dispatch_num} Completed")
                
                dispatches.append(dispatch)
                
            db.commit()
            
            # Refresh all after commit
            for d in dispatches:
                db.refresh(d)
                
            return dispatches
            
        except Exception as e:
            db.rollback()
            logger.error(f"FCDispatch Batch failed: {str(e)}")
            FCDispatchService._log_audit(db, company_id, user_id, "FAILED", "FCDispatch", 0, f"Batch dispatch failed: {str(e)}")
            raise
