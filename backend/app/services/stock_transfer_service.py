from sqlalchemy.orm import Session
from app.models.schema import StockTransfer, Inventory, InventoryMovement

class StockTransferService:
    @staticmethod
    def complete_transfer(db: Session, transfer_id: int, invoice_id: int, user_id: int):
        from app.models.schema import Sale, SaleItem, StockTransferItem
        import uuid
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
            
            if qty > 0:
                # Add to destination (JSPL)
                dest_inv = db.query(Inventory).filter(
                    Inventory.company_id == transfer.to_company_id,
                    Inventory.product_id == item.product_id
                ).first()
                if dest_inv:
                    dest_inv.current_qty += qty
                    dest_inv.available_qty += qty
                    
                    mov_in = InventoryMovement(
                        company_id=transfer.to_company_id,
                        product_id=item.product_id,
                        warehouse_id=dest_inv.warehouse_id,
                        qty_before=dest_inv.current_qty - qty,
                        qty_changed=qty,
                        qty_after=dest_inv.current_qty,
                        source="Transfer In",
                        reference_id=transfer.transfer_number,
                        user_id=user_id
                    )
                    db.add(mov_in)
            
            # Track any unfulfilled quantities
            if qty < item.requested_qty:
                unfulfilled_items.append({
                    "product_id": item.product_id,
                    "requested_qty": item.requested_qty - qty
                })
                
        # Mark transfer as COMPLETED
        transfer.invoice_id = invoice_id
        transfer.status = "Completed"
        transfer.approved_by = user_id
        
        # If there are unfulfilled items, spawn a new pending transfer
        if unfulfilled_items:
            # Generate a backorder transfer number
            new_trf_num = f"{transfer.transfer_number}-BO"
            
            new_transfer = StockTransfer(
                transfer_number=new_trf_num,
                from_company_id=transfer.from_company_id,
                to_company_id=transfer.to_company_id,
                status="Pending",
                created_by=transfer.created_by,
                approved_by=None,
                total_value=0.0
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
                    unit_price=0.0,
                    total_value=0.0
                )
                db.add(new_item)
        transfer.approved_by = user_id
        
        db.commit()
        return transfer
