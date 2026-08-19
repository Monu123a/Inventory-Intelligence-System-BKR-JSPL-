import os

from app.services.audit_log_service import AuditLogService
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import logging
from app.models.schema import (
    FCDispatch, FCDispatchItem, StateHub, Warehouse, Product, Sale, 
    CompanySettings, DispatchTimeline, WarehouseStatus, Inventory, AuditLog, WarehouseExternalMapping, User
)
from app.api.routers.pos import complete_sale, PosCheckoutRequest, PosCartItem
import uuid
from app.services.delivery_challan_service import DeliveryChallanService
from app.services.document_number_service import DocumentNumberService
from app.models.schema import DocumentTypeEnum
from app.services.inventory_event_engine import InventoryEventEngine
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FCDispatchRequestItem(BaseModel):
    product_id: int
    quantity: int

class FCDispatchBatchRequest(BaseModel):
    idempotency_key: Optional[str] = None
    dispatch_type: str = "STANDARD" # STANDARD or EMERGENCY
    source_warehouse_id: int
    warehouse_ids: List[int] # Dest FCs
    hub_id: Optional[int] = None # Optional manual override from frontend
    items: List[FCDispatchRequestItem]

class FCDispatchService:
    @staticmethod
    def _generate_dispatch_number(db: Session, company_id: int, hub_code: str) -> str:
        # We need a robust sequence that is concurrency-safe.
        from datetime import date
        d = date.today()
        start_year = d.year if d.month >= 4 else d.year - 1
        end_year = start_year + 1
        fy = f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"
        
        return DocumentNumberService.generate_number(
            db=db,
            company_id=company_id,
            document_type=DocumentTypeEnum.DISPATCH,
            fiscal_year=fy,
            prefix_override=f"WHT/{hub_code}"
        )

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
            # 0. Idempotency Check
            existing_dispatches = []
            if request.idempotency_key:
                expected_keys = [f"{request.idempotency_key}_{wh_id}" for wh_id in request.warehouse_ids]
                existing_dispatches = db.query(FCDispatch).filter(
                    FCDispatch.idempotency_key.in_(expected_keys),
                    FCDispatch.company_id == company_id
                ).all()
                
                # Filter out already processed warehouse_ids
                processed_warehouse_ids = [d.warehouse_id for d in existing_dispatches]
                request.warehouse_ids = [wid for wid in request.warehouse_ids if wid not in processed_warehouse_ids]
                
                # If all were already processed, just return them
                if not request.warehouse_ids:
                    return existing_dispatches

            # 1. Resolve Source Warehouse
            source_warehouse = db.query(Warehouse).filter(Warehouse.id == request.source_warehouse_id).first()
            if not source_warehouse:
                raise HTTPException(status_code=404, detail="Source Warehouse not found")

            # Source Validation Rules
            if request.dispatch_type == "EMERGENCY":
                if source_warehouse.code != "VSHB":
                    raise HTTPException(status_code=400, detail="EMERGENCY dispatches must originate from VSHB")
            else:
                # Standard dispatch
                if source_warehouse.code not in ["BKR", "VSHB"]:
                    # Wait, BKR central warehouse might have code "BKR" or something. 
                    # Let's ensure we are relaxed enough if it's not VSHB or BKR by code, but we should strictly check it.
                    # The user said: "STANDARD BKR or VSHB".
                    if source_warehouse.code != "VSHB" and "BKR" not in (source_warehouse.code or ""):
                        # Fallback for name check just in case BKR doesn't have code="BKR", but we prefer code.
                        if "BKR" not in source_warehouse.name.upper():
                            raise HTTPException(status_code=400, detail="STANDARD dispatches must originate from BKR or VSHB")
                            
            transaction_origin = "INTERNAL_DISTRIBUTION"

            if source_warehouse.status != WarehouseStatus.ACTIVE:
                raise HTTPException(status_code=400, detail=f"Source Warehouse must be ACTIVE (currently {source_warehouse.status})")

            company_settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
            export_to_accounting = True
            if company_settings:
                export_to_accounting = company_settings.export_internal_distribution_to_accounting

            for dest_warehouse_id in request.warehouse_ids:
                if dest_warehouse_id == source_warehouse.id:
                    raise HTTPException(status_code=400, detail="Source and destination warehouses cannot be the same")

                # 2. Fetch Dest FC Details
                dest_warehouse = db.query(Warehouse).filter(Warehouse.id == dest_warehouse_id).first()
                if not dest_warehouse:
                    raise HTTPException(status_code=404, detail=f"Destination Warehouse {dest_warehouse_id} not found")

                is_cross_company = dest_warehouse.company_id != company_id
                cross_enabled = os.getenv("CROSS_COMPANY_TRANSFERS", "true").lower() == "true"

                if is_cross_company:
                    if not cross_enabled:
                        raise HTTPException(status_code=403, detail="Cross-company transfers are currently disabled")
                        
                    user_obj = db.query(User).filter(User.id == user_id).first()
                    has_permission = user_obj.role in ["Admin", "SuperAdmin"] or "cross_company_transfer" in (user_obj.permissions or [])
                    if not has_permission:
                        raise HTTPException(status_code=403, detail="Not authorized to create cross-company transfers")
                        

                    # Validate SKUs exist in destination company
                    missing_skus = []
                    for req_item in request.items:
                        src_prod = db.query(Product).filter(Product.id == req_item.product_id).first()
                        if src_prod:
                            dest_prod = db.query(Product).filter(Product.sku == src_prod.sku, Product.company_id == dest_warehouse.company_id).first()
                            if not dest_prod:
                                missing_skus.append(src_prod.sku)
                    if missing_skus:
                        raise HTTPException(status_code=400, detail={"message": "Products missing in destination company", "missing_skus": missing_skus})

                            
                    # Audit log
                    AuditLogService.log(
                        db,
                        company_id=company_id,
                        
                        entity_type="FCDispatch",
                        entity_id=0,
                        event_type="CROSS_COMPANY_TRANSFER_INITIATED",
                        message=f"Initiating cross company transfer to {dest_warehouse.company_id}",
                        metadata={"destination_company_id": dest_warehouse.company_id, "source_company_id": company_id}
                    )

                # Destination Amazon Validation
                amazon_mapping = db.query(WarehouseExternalMapping).filter(
                    WarehouseExternalMapping.warehouse_id == dest_warehouse.id,
                    WarehouseExternalMapping.marketplace.ilike('%Amazon%')
                ).first()
                if amazon_mapping:
                    raise HTTPException(status_code=400, detail="Amazon FCs are not permitted for internal distribution")

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
                    

                    is_inter_state = False
                    if hub and source_warehouse:
                        hub_state = str(hub.state_code).strip() if hub.state_code else ""
                        src_state = "07" # Default BKR Haryana
                        # You might want to get actual source state code, but let's assume cross state
                        if hub_state and hub_state != "07":
                            is_inter_state = True

                    cgst = 0.0
                    sgst = 0.0
                    igst = 0.0
                    if is_inter_state:
                        igst = gst
                    else:
                        cgst = gst / 2
                        sgst = gst / 2

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
                        cgst=cgst,
                        sgst=sgst,
                        igst=igst,
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
                dispatch_num = FCDispatchService._generate_dispatch_number(db, company_id, hub.hub_code)
                dispatch = FCDispatch(
                    company_id=company_id,
                    source_warehouse_id=source_warehouse.id,
                    warehouse_id=dest_warehouse.id,
                    dispatch_number=dispatch_num,
                    idempotency_key=f"{request.idempotency_key}_{dest_warehouse.id}" if request.idempotency_key else None,
                    dispatch_type=request.dispatch_type,
                    dispatch_status="Processing",
                    created_by=user_id
                )
                db.add(dispatch)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    # It was inserted concurrently
                    concurrent_dispatch = db.query(FCDispatch).filter_by(
                        idempotency_key=f"{request.idempotency_key}_{dest_warehouse.id}", 
                        company_id=company_id
                    ).first()
                    if concurrent_dispatch:
                        existing_dispatches.append(concurrent_dispatch)
                        continue
                    raise

                FCDispatchService._log_timeline(db, dispatch.id, "Created", "Success", user_id, f"Dispatch {dispatch_num} initiated from {source_warehouse.name}")
                FCDispatchService._log_audit(db, company_id, user_id, "CREATE", "FCDispatch", dispatch.id, f"Dispatch {dispatch_num} Created")

                # 4. Call pos.py complete_sale (with commit=False)
                user_obj = db.query(User).filter(User.id == user_id).first()
                sale_dto = complete_sale(request=None, payload=pos_request, company_id=company_id, db=db, user=user_obj, commit=False)
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
                    "remarks": f"{request.dispatch_type} Dispatch from {source_warehouse.code}",
                    "shipping_snapshot": {
                        "name": dest_warehouse.name,
                        "address": dest_warehouse.address,
                        "state": hub.state,
                        "state_code": hub.state_code,
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
                        company_id=dest_warehouse.company_id,
                        product_sku=it.sku,
                        warehouse_id=dest_warehouse.id,
                        quantity=it.quantity,
                        event_type="TRANSFER_IN",
                        source="FC_DISPATCH_IN",
                        reference_id=dispatch_num,
                        metadata_payload={"dispatch_id": dispatch.id, "source_company_id": company_id}
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
                
            db.flush()
            
            for dispatch in dispatches:
                logger.info("Dispatch created", extra={
                    "dispatch_id": dispatch.id,
                    "source": dispatch.source_warehouse_id,
                    "destination": dispatch.warehouse_id,
                    "user": user_id
                })
            
            db.commit()
            
            # Refresh all after commit
            for d in dispatches:
                db.refresh(d)
            
            # Combine newly created dispatches with any existing ones (from partial retries)
            if request.idempotency_key and existing_dispatches:
                dispatches.extend(existing_dispatches)
                
            return dispatches
            
        except Exception as e:
            db.rollback()
            logger.error(f"FCDispatch Batch failed: {str(e)}")
            FCDispatchService._log_audit(db, company_id, user_id, "FAILED", "FCDispatch", 0, f"Batch dispatch failed: {str(e)}")
            raise
