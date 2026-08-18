from sqlalchemy.orm import Session
from app.models.schema import StockTransfer, Inventory, Product
from app.models.schema import SaleItem, StockTransferItem
from app.services.inventory_event_engine import InventoryEventEngine
from app.models.schema import Warehouse
from app.services.transfer_number_service import TransferNumberService
from app.services.audit_log_service import AuditLogService

class StockTransferService:
    @staticmethod
    def approve_transfer(db: Session, transfer_id: int, user_id: int):
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer:
            raise ValueError("Transfer not found")
        if transfer.status != "Pending":
            raise ValueError("Transfer is not in Pending state")
        transfer.status = "Approved"
        transfer.approved_by = user_id
        db.flush()
        return transfer

    @staticmethod
    def complete_transfer_locked(db: Session, transfer: StockTransfer, invoice_id: int, user_id: int):
        if transfer.status not in ("Pending", "Approved"):
            raise ValueError("Transfer cannot be completed. It might already be processed.")
            
        # Get actual quantities fulfilled from the invoice
        fulfilled_qty_map = {}
        sale_items = db.query(SaleItem).filter(SaleItem.sale_id == invoice_id).all()
        for si in sale_items:
            fulfilled_qty_map[si.product_id] = si.quantity
            
        unfulfilled_items = []

        for item in transfer.items:
            qty = fulfilled_qty_map.get(item.product_id, 0)
            
            if qty <= 0:
                # Nothing fulfilled for this item
                if item.requested_qty > 0:
                    unfulfilled_items.append({
                        "product_id": item.product_id,
                        "requested_qty": item.requested_qty,
                        "unit_price": item.unit_price or 0.0
                    })
                continue

            # Get product sku
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                continue

            # ===== ADD to DESTINATION (JSPL) =====
            # check dest_warehouse first
            dest_warehouse = db.query(Warehouse).filter(
                Warehouse.company_id == transfer.to_company_id
            ).first()
            if not dest_warehouse:
                raise ValueError(f"Destination company {transfer.to_company_id} has no warehouse.")

            # ===== DEDUCT from SOURCE (BKR) =====
            source_invs = db.query(Inventory).filter(
                Inventory.company_id == transfer.from_company_id,
                Inventory.product_id == item.product_id
            ).with_for_update().all()
            
            requested_qty = qty
            total_available = sum((inv.current_qty - (inv.reserved_qty or 0)) for inv in source_invs)
            
            print(f"[TRANSFER CHECK] Requested: {requested_qty}, Available: {total_available}")
            
            if total_available < requested_qty:
                raise ValueError(
                    f"Insufficient stock for {product.sku}: {total_available} available, {requested_qty} requested"
                )
                
            remaining_deduct = requested_qty
            actual_deducted = 0
            

            for src_inv in source_invs:
                if remaining_deduct <= 0:
                    break
                available_in_this = src_inv.current_qty - (src_inv.reserved_qty or 0)
                deduct_from_this = min(remaining_deduct, available_in_this)
                if deduct_from_this <= 0:
                    continue
                    
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=transfer.from_company_id,
                    product_sku=product.sku,
                    warehouse_id=src_inv.warehouse_id,
                    quantity=deduct_from_this,
                    event_type="TRANSFER_OUT",
                    source="Transfer Out",
                    reference_id=transfer.transfer_number,
                    user_id=user_id,
                    metadata_payload={"destination_company_id": transfer.to_company_id}
                )
                actual_deducted += deduct_from_this
                remaining_deduct -= deduct_from_this

            # ===== ADD to DESTINATION (JSPL) =====
            if actual_deducted > 0:
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=transfer.to_company_id,
                    product_sku=product.sku,
                    warehouse_id=dest_warehouse.id,
                    quantity=actual_deducted,
                    event_type="TRANSFER_IN",
                    source="Transfer In",
                    reference_id=transfer.transfer_number,
                    user_id=user_id,
                    metadata_payload={"source_company_id": transfer.from_company_id}
                )

            # Track unfulfilled quantities for backorder
            if actual_deducted < item.requested_qty:
                unfulfilled_items.append({
                    "product_id": item.product_id,
                    "requested_qty": item.requested_qty - actual_deducted,
                    "unit_price": item.unit_price or 0.0
                })
                
        # Mark transfer as COMPLETED
        transfer.invoice_id = invoice_id
        transfer.status = "Completed"
        transfer.approved_by = user_id
        
        AuditLogService.log(
            db,
            company_id=transfer.from_company_id,
            entity_type="StockTransfer",
            entity_id=transfer.id,
            event_type="TRANSFER_COMPLETED",
            message=f"Stock transfer {transfer.transfer_number} completed",
            metadata={"from_company": transfer.from_company_id, "to_company": transfer.to_company_id, "invoice_id": invoice_id}
        )
        
        # If there are unfulfilled items, spawn a new pending transfer
        if unfulfilled_items:
            # Generate a proper unique backorder transfer number
            new_trf_num = TransferNumberService.generate_next(
                db, company_id=transfer.from_company_id
            )
            
            new_transfer = StockTransfer(
                transfer_number=new_trf_num,
                from_company_id=transfer.from_company_id,
                to_company_id=transfer.to_company_id,
                status="Pending",
                created_by=transfer.created_by,
                approved_by=None,
                total_value=0.0,
                notes=f"Backorder from {transfer.transfer_number}"
            )
            db.add(new_transfer)
            db.flush()
            
            for ui in unfulfilled_items:
                new_item = StockTransferItem(
                    transfer_id=new_transfer.id,
                    product_id=ui["product_id"],
                    requested_qty=ui["requested_qty"],
                    approved_qty=0,
                    dispatched_qty=0,
                    received_qty=0,
                    unit_price=ui["unit_price"],
                    total_value=ui["unit_price"] * ui["requested_qty"]
                )
                db.add(new_item)
        
        db.flush()
        return transfer
