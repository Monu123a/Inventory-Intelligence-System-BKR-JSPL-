import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException
from app.models.schema import Inventory, InventoryMovement, Product, Alert
from app.services.metrics_service import log_metric
import time

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
        metadata_payload: Optional[dict] = None,
        allow_negative_stock: bool = False
    ) -> InventoryMovement:
        """
        The single source of truth for all inventory modifications.
        """
        # 1. Enforce Idempotency Key (Operation ID)
        actual_metadata = metadata_payload or {}
        op_id = actual_metadata.get("operation_id")
        if not op_id:
            line_id = actual_metadata.get("line_id", "")
            # Deterministic idempotency key to prevent double processing
            op_id = f"{event_type}_{reference_id}_{product_sku}_{warehouse_id}_{line_id}".strip("_")
            actual_metadata["operation_id"] = op_id
            
        # 2. Check if already processed (Idempotency)
        existing_event = db.query(InventoryMovement).filter_by(operation_id=op_id).first()
        if existing_event:
            logger.info(f"Idempotency match: skipping inventory update for operation_id {op_id}")
            return existing_event

        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                with db.begin_nested(): # SAVEPOINT
                    # Guard against negative quantities
                    if quantity < 0:
                        raise ValueError('Quantity must be positive. Use event_type DEDUCT for removals.')
                        
                    # Ensure product exists for this company
                    # Globally enforce the 6-character SKU rule
                    product_sku = product_sku.strip().upper()
                    product = db.query(Product).filter(Product.sku == product_sku, Product.company_id == company_id).first()
                    if not product:
                        raise ValueError(f"Product SKU {product_sku} not found for company {company_id}.")
            
                    # Get current inventory with row-level lock
                    inventory = db.query(Inventory).filter(
                        Inventory.product_id == product.id,
                        Inventory.warehouse_id == warehouse_id,
                        Inventory.company_id == company_id
                    ).with_for_update().first()

                    if not inventory:
                        inventory = Inventory(
                            company_id=company_id,
                            product_id=product.id,
                            warehouse_id=warehouse_id
                        )
                        inventory._allow_mutation = True
                        inventory.current_qty = 0
                        inventory.reserved_qty = 0
                        inventory.available_qty = 0
                        db.add(inventory)
                        db.flush()

                    inventory._allow_mutation = True
                    qty_before = inventory.current_qty
                    qty_changed = 0

                    # Handle Explicit Business Events
                    if event_type in ("ADD", "OPENING_BALANCE"):
                        qty_changed = quantity
                        inventory.current_qty += quantity

                    elif event_type == "RETURN":
                        qty_changed = quantity
                        inventory.current_qty += quantity
                    
                    elif event_type == "TRANSFER_IN":
                        qty_changed = quantity
                        inventory.current_qty += quantity
                
                    elif event_type == "RESTOCK":
                        qty_changed = quantity
                        inventory.current_qty += quantity
                        
                    elif event_type == "DEDUCT":
                        qty_changed = -quantity
                        inventory.current_qty -= quantity
                        
                    elif event_type == "TRANSFER_OUT":
                        qty_changed = -quantity
                        inventory.current_qty -= quantity
                
                    elif event_type == "ADJ_MINUS":
                        qty_changed = -quantity
                        inventory.current_qty -= quantity
                        
                    elif event_type == "DAMAGE_WRITE_OFF":
                        qty_changed = -quantity
                        inventory.current_qty -= quantity
    
                    elif event_type == "SALE":
                        qty_changed = -quantity
                        inventory.current_qty -= quantity
                        
                    elif event_type == "REPLACE":
                        qty_changed = quantity - qty_before
                        inventory.current_qty = quantity
                        
                    elif event_type in ("RESERVE", "RESERVED"):
                        qty_changed = 0  # Does not change current_qty
                        inventory.reserved_qty = (inventory.reserved_qty or 0) + quantity
                
                    elif event_type == "UNRESERVE":
                        qty_changed = 0  # Does not change current_qty
                        if inventory.reserved_qty and inventory.reserved_qty >= quantity:
                            inventory.reserved_qty -= quantity
                        elif inventory.reserved_qty and inventory.reserved_qty > 0:
                            inventory.reserved_qty = 0
                            
                    else:
                        raise ValueError(f"Unknown event_type: {event_type}")

                # Keep available_qty in sync: available = current - reserved
                inventory.available_qty = inventory.current_qty - (inventory.reserved_qty or 0)
                
                # Enforce available_qty >= 0 (unless allow_negative_stock is True)
                if inventory.available_qty < 0 and not allow_negative_stock:
                    print(f"[NEGATIVE STOCK ATTEMPT] product_sku={product_sku}, available_qty is negative, requested={quantity}, allowed_flag={allow_negative_stock}")
                    raise ValueError(f"Insufficient stock for {product_sku}: cannot deduct {quantity} because available stock would drop below zero")
                
                # Explicit Inventory Reconciliation Verification
                if inventory.available_qty != inventory.current_qty - (inventory.reserved_qty or 0):
                     inventory._allow_mutation = False
                     raise ValueError("Inventory reconciliation failed: Available Qty must equal Current Qty - Reserved Qty")

                qty_after = inventory.current_qty
                inventory._allow_mutation = False
                
                # Inject explicit event_type into metadata_payload for history tracking
                actual_metadata = metadata_payload or {}
                actual_metadata["event_type"] = event_type
        
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
                    operation_id=op_id,
                    user_id=user_id,
                    metadata_payload=actual_metadata
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

                db.flush() # Force OCC check
                logger.info(f"Inventory Event: {source} [{reference_id}] | SKU: {product_sku} | {qty_before} -> {qty_after}")
                return movement

            except StaleDataError:
                if attempt == MAX_RETRIES - 1:
                    raise HTTPException(
                        status_code=409,
                        detail="Concurrent modification detected. Please retry."
                    )
                # rollback the savepoint happens automatically by db.begin_nested() context manager on exception
                
            except OperationalError as e:
                if "database is locked" in str(e).lower():
                    logger.warning(f"DB_LOCK_RETRY | attempt={attempt+1} | user={user_id}")
                    log_metric("inventory_write_conflict", 1)
                    if attempt == MAX_RETRIES - 1:
                        raise HTTPException(
                            status_code=503,
                            detail="System busy. Please retry."
                        )
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise
