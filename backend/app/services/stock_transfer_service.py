from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.schema import StockTransfer, Inventory, InventoryMovement, Product

class StockTransferService:
    @staticmethod
    def complete_transfer(db: Session, transfer_id: int, invoice_id: int, user_id: int):
        from app.models.schema import Sale, SaleItem, StockTransferItem
        from app.services.transfer_number_service import TransferNumberService
        from datetime import datetime

        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer or transfer.status != "Pending":
            raise ValueError("Transfer cannot be completed. It might already be processed or not in Pending state.")
            
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

            # ===== DEDUCT from SOURCE (BKR) =====
            # Aggregate across all warehouses for the source company
            source_invs = db.query(Inventory).filter(
                Inventory.company_id == transfer.from_company_id,
                Inventory.product_id == item.product_id
            ).all()
            
            remaining_deduct = qty
            for src_inv in source_invs:
                if remaining_deduct <= 0:
                    break
                deduct_from_this = min(remaining_deduct, src_inv.current_qty)
                if deduct_from_this <= 0:
                    continue
                    
                src_inv.current_qty -= deduct_from_this
                src_inv.available_qty = max(0, src_inv.current_qty - (src_inv.reserved_qty or 0))
                
                mov_out = InventoryMovement(
                    company_id=transfer.from_company_id,
                    product_id=item.product_id,
                    warehouse_id=src_inv.warehouse_id,
                    qty_before=src_inv.current_qty + deduct_from_this,
                    qty_changed=-deduct_from_this,
                    qty_after=src_inv.current_qty,
                    source="Transfer Out",
                    reference_id=transfer.transfer_number,
                    user_id=user_id,
                    metadata_payload={"destination_company_id": transfer.to_company_id}
                )
                db.add(mov_out)
                remaining_deduct -= deduct_from_this

            # ===== ADD to DESTINATION (JSPL) =====
            dest_inv = db.query(Inventory).filter(
                Inventory.company_id == transfer.to_company_id,
                Inventory.product_id == item.product_id
            ).first()
            
            if not dest_inv:
                # Create inventory record if it doesn't exist
                # Find a default warehouse for the destination company
                from app.models.schema import Warehouse
                dest_warehouse = db.query(Warehouse).filter(
                    Warehouse.company_id == transfer.to_company_id
                ).first()
                if dest_warehouse:
                    dest_inv = Inventory(
                        company_id=transfer.to_company_id,
                        product_id=item.product_id,
                        warehouse_id=dest_warehouse.id,
                        current_qty=0,
                        reserved_qty=0,
                        available_qty=0
                    )
                    db.add(dest_inv)
                    db.flush()
                    
            if dest_inv:
                qty_before = dest_inv.current_qty
                dest_inv.current_qty += qty
                dest_inv.available_qty = dest_inv.current_qty - (dest_inv.reserved_qty or 0)
                
                mov_in = InventoryMovement(
                    company_id=transfer.to_company_id,
                    product_id=item.product_id,
                    warehouse_id=dest_inv.warehouse_id,
                    qty_before=qty_before,
                    qty_changed=qty,
                    qty_after=dest_inv.current_qty,
                    source="Transfer In",
                    reference_id=transfer.transfer_number,
                    user_id=user_id,
                    metadata_payload={"source_company_id": transfer.from_company_id}
                )
                db.add(mov_in)
            
            # Track unfulfilled quantities for backorder
            if qty < item.requested_qty:
                unfulfilled_items.append({
                    "product_id": item.product_id,
                    "requested_qty": item.requested_qty - qty,
                    "unit_price": item.unit_price or 0.0
                })
                
        # Mark transfer as COMPLETED
        transfer.invoice_id = invoice_id
        transfer.status = "Completed"
        transfer.approved_by = user_id
        
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
        
        db.commit()
        return transfer
