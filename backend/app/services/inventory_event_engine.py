import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.schema import Inventory, InventoryMovement, Product, Alert

logger = logging.getLogger("inventory.event_engine")

class InventoryEventEngine:
    
    @staticmethod
    def process_event(
        db: Session,
        company_id: int,
        product_sku: str,
        warehouse_id: int,
        quantity: int,
        event_type: str, # "ADD", "REPLACE", "DEDUCT"
        source: str,
        reference_id: str,
        user_id: Optional[int] = None,
        metadata_payload: Optional[dict] = None
    ) -> InventoryMovement:
        """
        The single source of truth for all inventory modifications.
        """
        # Guard against negative quantities
        if quantity < 0:
            raise ValueError(f"Quantity must be non-negative, got {quantity}")
        # Ensure product exists for this company
        product = db.query(Product).filter(Product.sku == product_sku, Product.company_id == company_id).first()
        if not product:
            logger.warning(f"Product SKU {product_sku} not found for company {company_id}. Creating placeholder.")
            product = Product(sku=product_sku, name=f"Unknown SKU {product_sku}", company_id=company_id)
            db.add(product)
            db.flush()

        # Get current inventory
        inventory = db.query(Inventory).filter(
            Inventory.product_id == product.id,
            Inventory.warehouse_id == warehouse_id,
            Inventory.company_id == company_id
        ).first()

        if not inventory:
            inventory = Inventory(
                company_id=company_id,
                product_id=product.id,
                warehouse_id=warehouse_id,
                current_qty=0,
                reserved_qty=0,
                available_qty=0
            )
            db.add(inventory)
            db.flush()

        qty_before = inventory.current_qty
        qty_changed = 0

        if event_type == "ADD":
            qty_changed = quantity
            inventory.current_qty += quantity
        elif event_type in ["DEDUCT", "SALE"]:
            qty_changed = -quantity
            inventory.current_qty -= quantity
        elif event_type == "REPLACE":
            qty_changed = quantity - qty_before
            inventory.current_qty = quantity
        else:
            raise ValueError(f"Unknown event_type: {event_type}")

        # Keep available_qty in sync
        inventory.available_qty = inventory.current_qty - inventory.reserved_qty

        qty_after = inventory.current_qty
        
        # Record Movement
        movement = InventoryMovement(
            company_id=company_id,
            product_id=product.id,
            warehouse_id=warehouse_id,
            qty_before=qty_before,
            qty_changed=qty_changed,
            qty_after=qty_after,
            source=source,
            reference_id=reference_id,
            user_id=user_id,
            metadata_payload=metadata_payload or {}
        )
        db.add(movement)
        
        # Check alerts
        min_stock_level = product.min_stock_level or 0
        alert_type = None
        alert_message = None

        if qty_after < 0:
            alert_type = "NegativeStock"
            alert_message = f"Product {product_sku} has negative stock ({qty_after}) in warehouse {warehouse_id}."
        elif min_stock_level > 0 and qty_after < min_stock_level:
            alert_type = "LowStock"
            alert_message = f"Product {product_sku} has dropped below min stock ({qty_after} < {min_stock_level}) in warehouse {warehouse_id}."

        if alert_type and alert_message:
            existing_alert = db.query(Alert).filter(
                Alert.company_id == company_id,
                Alert.alert_type == alert_type,
                Alert.message == alert_message,
                Alert.is_resolved == False
            ).first()
            if not existing_alert:
                db.add(Alert(
                    company_id=company_id,
                    alert_type=alert_type,
                    message=alert_message
                ))

        db.flush()
        
        logger.info(f"Inventory Event: {source} [{reference_id}] | SKU: {product_sku} | {qty_before} -> {qty_after}")
        
        return movement
