from sqlalchemy.orm import Session
from app.models.schema import StockTransfer, Inventory, InventoryMovement

class StockTransferService:
    @staticmethod
    def complete_transfer(db: Session, transfer_id: int, invoice_id: int, user_id: int):
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer or transfer.status != "Pending":
            raise ValueError("Transfer cannot be completed. It might already be processed or not in Pending state.")
            
        for item in transfer.items:
            qty = item.requested_qty
            
            # Add to destination (JSPL)
            dest_inv = db.query(Inventory).filter(
                Inventory.company_id == transfer.to_company_id,
                Inventory.product_id == item.product_id
            ).first()
            if dest_inv:
                dest_inv.current_qty += qty
                
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
                
        # Mark transfer as COMPLETED
        transfer.invoice_id = invoice_id
        transfer.status = "Completed"
        transfer.approved_by = user_id
        
        db.commit()
        return transfer
