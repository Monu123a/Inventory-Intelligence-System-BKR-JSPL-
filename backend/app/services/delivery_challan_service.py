import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.schema import DeliveryChallan, DeliveryChallanItem
from app.models.schema import SaleItem
from app.models.schema import Sale

class DeliveryChallanService:

    @staticmethod
    def create_challan(db: Session, company_id: int, challan_data: dict, user_id: int = None) -> DeliveryChallan:
        challan_number = challan_data.get("challan_number")
        if not challan_number:
            challan_number = f"DC-{uuid.uuid4().hex[:8].upper()}"

        sale_id = challan_data.get("sale_id")
        
        seller_snapshot = challan_data.get("seller_snapshot")
        buyer_snapshot = challan_data.get("buyer_snapshot")
        
        if sale_id and (not seller_snapshot or not buyer_snapshot):
            sale = db.query(Sale).filter(Sale.id == sale_id).first()
            if sale:
                if not seller_snapshot:
                    seller_snapshot = {
                        "name": sale.company_name_snapshot,
                        "gstin": sale.company_gstin_snapshot,
                        "address": sale.company_address_snapshot
                    }
                if not buyer_snapshot:
                    buyer_snapshot = {
                        "name": sale.customer_name,
                        "gstin": sale.customer_gstin,
                        "address": sale.customer_address,
                        "state": sale.customer_state
                    }

        challan = DeliveryChallan(
            company_id=company_id,
            challan_number=challan_number,
            sale_id=sale_id,
            seller_snapshot=seller_snapshot,
            buyer_snapshot=buyer_snapshot,
            shipping_snapshot=challan_data.get("shipping_snapshot"),
            vehicle_number=challan_data.get("vehicle_number"),
            transport_mode=challan_data.get("transport_mode"),
            eway_bill=challan_data.get("eway_bill"),
            remarks=challan_data.get("remarks"),
            status="Draft",
            created_by=user_id
        )
        db.add(challan)
        db.flush()

        items_to_add = challan_data.get("items", [])
        if not items_to_add and challan.sale_id:
            sale_items = db.query(SaleItem).filter(SaleItem.sale_id == challan.sale_id).all()
            items_to_add = [
                {
                    "product_id": si.product_id,
                    "sku_snapshot": si.sku,
                    "product_name_snapshot": si.product_name,
                    "hsn_snapshot": si.hsn_sac,
                    "unit_snapshot": si.unit,
                    "quantity": si.quantity,
                    "unit_price": si.selling_price,
                    "tax_rate": si.gst_rate,
                    "tax_amount": si.cgst + si.sgst + si.igst,
                    "total_price": si.line_total
                }
                for si in sale_items
            ]

        for item in items_to_add:
            dc_item = DeliveryChallanItem(
                challan_id=challan.id,
                product_id=item.get("product_id"),
                sku_snapshot=item.get("sku_snapshot"),
                product_name_snapshot=item.get("product_name_snapshot"),
                hsn_snapshot=item.get("hsn_snapshot"),
                unit_snapshot=item.get("unit_snapshot"),
                quantity=item.get("quantity", 0),
                unit_price=item.get("unit_price", 0.0),
                tax_rate=item.get("tax_rate", 0.0),
                tax_amount=item.get("tax_amount", 0.0),
                total_price=item.get("total_price", 0.0)
            )
            db.add(dc_item)
        
        db.flush()
        return challan

    @staticmethod
    def print_challan(db: Session, company_id: int, challan_id: int):
        challan = db.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id, DeliveryChallan.company_id == company_id).first()
        if not challan:
            raise ValueError("DeliveryChallan not found")
        
        challan.status = "Printed"
        challan.print_count = (challan.print_count or 0) + 1
        challan.last_printed_at = datetime.utcnow()
        db.flush()
        return challan
    
    @staticmethod
    def cancel_challan(db: Session, company_id: int, challan_id: int):
        challan = db.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id, DeliveryChallan.company_id == company_id).first()
        if not challan:
            raise ValueError("DeliveryChallan not found")
        
        challan.status = "Cancelled"
        db.flush()
        return challan
