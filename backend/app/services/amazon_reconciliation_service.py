import io
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session

from app.models.schema import (
    AmazonLiveAllocation, AmazonDLQ, DLQType, AllocationStatus, 
    Warehouse, Product, WarehouseType, AmazonOrderEventLog
)
from app.services.inventory_event_engine import InventoryEventEngine

logger = logging.getLogger(__name__)

class AmazonReconciliationService:
    @staticmethod
    def process_report_item(db: Session, company_id: int, report_item: dict) -> bool:
        """
        Process a single item from an Amazon Settlement/Fulfillment Report.
        Requires strict matching on (order_id, sku, amazon_line_item_id).
        """
        order_id = report_item.get("order_id")
        sku = str(report_item.get("sku", "")).strip().upper()
        line_item_id = report_item.get("amazon_line_item_id")
        shipped_qty = int(report_item.get("shipped_quantity", 0))
        is_return = report_item.get("is_return", False)
        fc_code = report_item.get("fc", report_item.get("fulfillment_center_id", "")).strip().upper()
        
        try:
            with db.begin_nested():
                # Resolve warehouse if FC code is given
                target_wh_id = None
                if fc_code:
                    wh = db.query(Warehouse).filter(Warehouse.company_id == company_id, Warehouse.code == fc_code).first()
                    if wh:
                        target_wh_id = wh.id

                # 1. Lock the allocation row
                alloc_query = db.query(AmazonLiveAllocation).filter(
                    AmazonLiveAllocation.order_id == order_id,
                    AmazonLiveAllocation.sku == sku,
                    AmazonLiveAllocation.company_id == company_id
                )
                if line_item_id and line_item_id != "default":
                    alloc_query = alloc_query.filter(AmazonLiveAllocation.amazon_line_item_id == line_item_id)
                
                allocation = alloc_query.with_for_update().first()
                
                wh_id = target_wh_id or (allocation.warehouse_id if allocation else None)
                if not wh_id:
                    central_wh = db.query(Warehouse).filter(
                        Warehouse.company_id == company_id, 
                        Warehouse.warehouse_type == WarehouseType.CENTRAL
                    ).first()
                    wh_id = central_wh.id if central_wh else None

                if is_return:
                    # Return Restitution
                    if wh_id:
                        InventoryEventEngine.process_event(
                            db=db,
                            company_id=company_id,
                            product_sku=sku,
                            warehouse_id=wh_id,
                            quantity=shipped_qty,
                            event_type="ADD",
                            source="Amazon_Return",
                            reference_id=f"{order_id}_{sku}_{line_item_id}_ADD",
                            metadata_payload={"report_item": report_item}
                        )
                    if allocation:
                        allocation.status = AllocationStatus.RETURNED
                        allocation.closed = True
                        allocation.allocated_qty = allocation.reconciled_qty
                        allocation.updated_at = datetime.utcnow()
                    return True
                    
                # Forward Reconciliation (Shipment)
                if shipped_qty <= 0:
                    return True # Nothing to deduct
                    
                delta_to_deduct = shipped_qty
                if allocation:
                    new_reconciled = max(allocation.reconciled_qty, allocation.reconciled_qty + shipped_qty)
                    delta_to_deduct = new_reconciled - allocation.reconciled_qty
                    allocation.reconciled_qty = new_reconciled
                    allocation.updated_at = datetime.utcnow()
                    if target_wh_id:
                        allocation.warehouse_id = target_wh_id
                    if allocation.reconciled_qty >= allocation.allocated_qty:
                        allocation.closed = True
                        allocation.status = AllocationStatus.SHIPPED

                if delta_to_deduct > 0 and wh_id:
                    # Hard Deduction via Event Engine
                    op_id = f"FBA_DEDUCT_{order_id}_{sku}_{fc_code}_{line_item_id}".strip("_")
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=company_id,
                        product_sku=sku,
                        warehouse_id=wh_id,
                        quantity=delta_to_deduct,
                        event_type="DEDUCT",
                        source="Amazon_FBA_Shipment",
                        reference_id=f"{order_id}_{fc_code}",
                        metadata_payload={"report_item": report_item, "operation_id": op_id},
                        allow_negative_stock=True
                    )
                        
            return True
        except Exception as e:
            logger.error(f"Failed to reconcile item {sku} for order {order_id}: {e}")
            dlq = AmazonDLQ(
                company_id=company_id,
                dlq_type=DLQType.DATA_MISMATCH,
                reference_id=order_id,
                error_message=str(e),
                payload=report_item
            )
            db.add(dlq)
            return False

    @staticmethod
    def reconcile_fc_shipment_report(
        db: Session, 
        company_id: int, 
        report_data: Any,
        allow_negative_stock: bool = True
    ) -> Dict[str, Any]:
        """
        Parses an Amazon Fulfilled Shipments Report / All Orders Report (DataFrame, TSV/CSV text, or bytes),
        matches the physical Fulfillment Center (FC column, e.g. BLR8, BOM7, MAA4) to our warehouses,
        permanently deducts physical inventory from that specific FC warehouse, and reconciles soft allocations.
        """
        # 1. Parse report input into pandas DataFrame
        df = None
        if isinstance(report_data, pd.DataFrame):
            df = report_data
        elif isinstance(report_data, (str, bytes)):
            text_data = report_data.decode("utf-8", errors="replace") if isinstance(report_data, bytes) else report_data
            try:
                # First try comma separated
                df = pd.read_csv(io.StringIO(text_data))
                if len(df.columns) <= 1:
                    # Try tab separated
                    df = pd.read_csv(io.StringIO(text_data), sep="\t")
            except Exception:
                df = pd.read_csv(io.StringIO(text_data), sep=None, engine="python")

        if df is None or df.empty:
            return {
                "status": "FAILED",
                "message": "Empty or unparseable shipment report",
                "rows_processed": 0,
                "deductions_applied": 0,
                "fc_breakdown": {}
            }

        # 2. Normalize column headers
        col_map = {}
        for c in df.columns:
            clean = str(c).strip().replace('"', '').replace("'", "")
            lower_clean = clean.lower().replace("-", " ").replace("_", " ")
            if "order id" in lower_clean and "item" not in lower_clean and "merchant" not in lower_clean:
                col_map["order_id"] = c
            elif "order item id" in lower_clean and "merchant" not in lower_clean:
                col_map["line_item_id"] = c
            elif lower_clean in ("merchant sku", "sku", "seller sku"):
                col_map["sku"] = c
            elif "shipped quantity" in lower_clean or lower_clean in ("quantity", "qty", "shipped qty"):
                col_map["quantity"] = c
            elif lower_clean in ("fc", "fulfillment center id", "fulfillment center"):
                col_map["fc"] = c
            elif "shipment date" in lower_clean or lower_clean == "date":
                col_map["shipment_date"] = c

        if "order_id" not in col_map or "sku" not in col_map:
            return {
                "status": "FAILED",
                "message": f"Missing required columns in report. Found: {list(df.columns)}",
                "rows_processed": 0
            }

        # 3. Cache warehouses and products for quick resolution
        warehouses = db.query(Warehouse).filter(Warehouse.company_id == company_id).all()
        wh_code_map = {w.code.strip().upper(): w.id for w in warehouses if w.code}
        central_wh = next((w for w in warehouses if w.warehouse_type == WarehouseType.CENTRAL), warehouses[0] if warehouses else None)

        products = db.query(Product.id, Product.sku).filter(Product.company_id == company_id).all()
        known_skus = {p.sku.strip().upper(): p.id for p in products if p.sku}

        counters = {
            "rows_processed": 0,
            "deductions_applied": 0,
            "units_deducted": 0,
            "allocations_reconciled": 0,
            "fc_breakdown": {},
            "unknown_skus": set(),
            "unmapped_fcs": set()
        }

        # 4. Iterate and deduct per FC
        for _, row in df.iterrows():
            counters["rows_processed"] += 1
            order_id = str(row[col_map["order_id"]]).strip()
            raw_sku = str(row[col_map["sku"]]).strip()
            sku = raw_sku.upper()
            
            qty_col = col_map.get("quantity")
            try:
                shipped_qty = int(float(row[qty_col])) if qty_col and pd.notna(row[qty_col]) else 1
            except Exception:
                shipped_qty = 1

            if shipped_qty <= 0:
                continue

            fc_col = col_map.get("fc")
            fc_code = str(row[fc_col]).strip().upper() if fc_col and pd.notna(row[fc_col]) else ""
            line_item_id = str(row[col_map["line_item_id"]]).strip() if "line_item_id" in col_map and pd.notna(row[col_map["line_item_id"]]) else "default"

            # Check SKU validity
            if sku not in known_skus:
                counters["unknown_skus"].add(sku)
                dlq = AmazonDLQ(
                    company_id=company_id,
                    dlq_type=DLQType.DATA_MISMATCH,
                    reference_id=order_id,
                    error_message=f"Unknown SKU in shipment report: {sku}",
                    payload={"order_id": order_id, "sku": sku, "fc": fc_code, "quantity": shipped_qty}
                )
                db.add(dlq)
                continue

            # Resolve target FC warehouse
            target_wh_id = None
            if fc_code and fc_code in wh_code_map:
                target_wh_id = wh_code_map[fc_code]
            elif fc_code == "VSHB" or not fc_code:
                target_wh_id = central_wh.id if central_wh else None
            else:
                counters["unmapped_fcs"].add(fc_code)
                dlq = AmazonDLQ(
                    company_id=company_id,
                    dlq_type=DLQType.MATCH_FAILED,
                    reference_id=order_id,
                    error_message=f"Unmapped Amazon FC code: {fc_code}",
                    payload={"order_id": order_id, "sku": sku, "fc": fc_code, "quantity": shipped_qty}
                )
                db.add(dlq)
                continue

            try:
                # Deduct stock specifically from this FC warehouse
                op_id = f"FBA_DEDUCT_{order_id}_{sku}_{fc_code}_{line_item_id}".strip("_")
                movement = InventoryEventEngine.process_event(
                    db=db,
                    company_id=company_id,
                    product_sku=sku,
                    warehouse_id=target_wh_id,
                    quantity=shipped_qty,
                    event_type="DEDUCT",
                    source="Amazon_FBA_Shipment",
                    reference_id=f"{order_id}_{fc_code}",
                    metadata_payload={
                        "order_id": order_id,
                        "fc": fc_code,
                        "line_item_id": line_item_id,
                        "operation_id": op_id
                    },
                    allow_negative_stock=allow_negative_stock
                )

                # Update / reconcile corresponding live allocation
                alloc = db.query(AmazonLiveAllocation).filter(
                    AmazonLiveAllocation.company_id == company_id,
                    AmazonLiveAllocation.order_id == order_id,
                    AmazonLiveAllocation.sku == sku
                ).first()

                if alloc:
                    # Associate allocation specifically with the physical FC that dispatched it
                    alloc.warehouse_id = target_wh_id
                    alloc.reconciled_qty = max(alloc.reconciled_qty, alloc.reconciled_qty + shipped_qty)
                    if alloc.reconciled_qty >= alloc.allocated_qty:
                        alloc.closed = True
                        alloc.status = AllocationStatus.SHIPPED
                    counters["allocations_reconciled"] += 1

                counters["deductions_applied"] += 1
                counters["units_deducted"] += shipped_qty
                counters["fc_breakdown"][fc_code or "CENTRAL"] = counters["fc_breakdown"].get(fc_code or "CENTRAL", 0) + shipped_qty

                # Commit batch every 25 rows to release locks
                if counters["rows_processed"] % 25 == 0:
                    db.commit()
            except Exception as item_err:
                logger.error(f"Error deducting FC inventory for order {order_id}, sku {sku}, fc {fc_code}: {item_err}")
                dlq = AmazonDLQ(
                    company_id=company_id,
                    dlq_type=DLQType.DATA_MISMATCH,
                    reference_id=order_id,
                    error_message=str(item_err),
                    payload={"order_id": order_id, "sku": sku, "fc": fc_code}
                )
                db.add(dlq)
                db.commit()

        db.commit()

        return {
            "status": "SUCCESS",
            "rows_processed": counters["rows_processed"],
            "deductions_applied": counters["deductions_applied"],
            "units_deducted": counters["units_deducted"],
            "allocations_reconciled": counters["allocations_reconciled"],
            "fc_breakdown": counters["fc_breakdown"],
            "unknown_skus": list(counters["unknown_skus"]),
            "unmapped_fcs": list(counters["unmapped_fcs"])
        }
