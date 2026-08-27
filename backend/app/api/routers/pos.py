from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.models.db import get_db
from app.models.schema import Company, Product, Warehouse, Inventory, Sale, SaleItem, CompanySettings, SalesReturn, SalesReturnItem, User
from app.api.dependencies import get_current_company_id, get_current_user
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.invoice_number_service import InvoiceNumberService
from app.services.tally_integration_service import TallyIntegrationService
from app.services.audit_log_service import AuditLogService
from app.services.metrics_service import log_metric
from app.core.limiter import limiter
from fastapi import Request
import logging

import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pos", tags=["POS"])

# --- Authorization Dependency ---
def get_pos_company_id(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)) -> int:
    """Allow BKR always. Allow JSPL only when ENABLE_POS_JSPL=true. Reject others."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=403, detail="Company not found.")

    allowed_codes = {"BKR"}
    if os.environ.get("ENABLE_POS_JSPL", "true").lower() == "true":
        allowed_codes.add("JSPL")

    if company.code not in allowed_codes:
        raise HTTPException(status_code=403, detail=f"POS is not enabled for {company.code}.")
    return company_id

# Keep old name as alias so nothing breaks if imported elsewhere
get_bkr_company_id = get_pos_company_id


def _resolve_default_warehouse(db: Session, company_id: int) -> Warehouse:
    """Resolve the default POS warehouse for any company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    company_code = company.code if company else "UNKNOWN"

    warehouses = db.query(Warehouse).filter(
        Warehouse.company_id == company_id,
        Warehouse.status == "ACTIVE"
    ).order_by(Warehouse.id.asc()).all()

    if not warehouses:
        raise HTTPException(status_code=400, detail=f"No active warehouse configured for {company_code}")

    if len(warehouses) == 1:
        return warehouses[0]

    # JSPL-specific override: strictly use VSHB (FC VSHB Chandigarh)
    if company_code == "JSPL":
        vshb = next((w for w in warehouses if (w.code or "").strip().upper() == "VSHB"), None)
        if vshb:
            return vshb
        raise HTTPException(status_code=400, detail="JSPL POS requires the 'VSHB' warehouse, but it was not found or is inactive.")

    preferred_codes = {"DEFAULT", f"{company_code}-DEFAULT", f"{company_code}_DEFAULT", "MAIN", "POS"}
    for warehouse in warehouses:
        code = (warehouse.code or "").strip().upper()
        name = (warehouse.name or "").strip().lower()
        if code in preferred_codes or "default" in name or "main" in name or "pos" in name:
            return warehouse

    raise HTTPException(
        status_code=400,
        detail=f"Multiple active {company_code} warehouses found. Mark one clearly as the default warehouse before using POS."
    )

# Keep old name as alias
_resolve_default_bkr_warehouse = _resolve_default_warehouse


def _generate_bill_number(company_code: str = "BKR") -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S%f")
    suffix = uuid4().hex[:6].upper()
    return f"{company_code}-{timestamp}-{suffix}"

# --- Pydantic Models ---
from pydantic import BaseModel, Field
from app.models.schema import StockTransfer
from app.services.tally_payload_builder import TallyPayloadBuilder
class PosCartItem(BaseModel):
    product_id: int
    sku: str
    product_name: Optional[str] = None
    hsn_sac: Optional[str] = None
    unit: Optional[str] = None
    quantity: int = Field(..., gt=0)
    selling_price: float
    discount: float = 0.0
    gst_rate: float
    taxable_amount: float
    cgst: float
    sgst: float
    igst: float = 0.0
    line_total: float

class PosCheckoutRequest(BaseModel):
    idempotency_key: Optional[str] = None
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_gstin: Optional[str] = None
    customer_address: Optional[str] = None
    customer_state: Optional[str] = None
    customer_state_code: Optional[str] = None
    place_of_supply: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

    shipping_name: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_state_code: Optional[str] = None
    shipping_gstin: Optional[str] = None

    invoice_type: str = "B2C"
    invoice_prefix: Optional[str] = None  # B2C | B2B
    custom_invoice_number: Optional[str] = None
    custom_invoice_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    delivery_note: Optional[str] = None
    delivery_note_date: Optional[datetime] = None
    dispatch_document_number: Optional[str] = None
    dispatch_through: Optional[str] = None
    destination: Optional[str] = None
    vehicle_number: Optional[str] = None
    lr_rr_number: Optional[str] = None
    terms_of_delivery: Optional[str] = None

    # Internal routing overrides (for cross-module calls)
    origin_warehouse_id: Optional[int] = None
    skip_inventory_update: bool = False

    payment_method: str
    payment_reference: Optional[str] = None
    payment_date: Optional[datetime] = None
    total_taxable_amount: float
    total_tax: float
    grand_total: float
    items: List[PosCartItem]

# --- Endpoints ---

@router.get("/products/search")
def search_products(q: str = "", warehouse_id: Optional[int] = None, company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    if not q or len(q) < 2:
        return []

    search_term = f"%{q}%"
    
    if warehouse_id:
        default_warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.company_id == company_id).first()
        if not default_warehouse:
            raise HTTPException(status_code=400, detail="Specified warehouse not found")
    else:
        default_warehouse = _resolve_default_bkr_warehouse(db, company_id)

    results = db.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.hsn,
        Product.unit,
        Product.brand,
        Product.category,
        Product.item_rate.label("default_price"),
        Product.default_gst_rate,
        func.coalesce(Inventory.available_qty, 0).label("available_stock")
    ).outerjoin(
        Inventory, 
        (Inventory.product_id == Product.id) & (Inventory.warehouse_id == default_warehouse.id)
    ).filter(
        Product.company_id == company_id,
        Product.status == "Active",
        (Product.sku.ilike(search_term)) | (Product.name.ilike(search_term))
    ).limit(20).all()

    return [
        {
            "id": r.id,
            "sku": r.sku,
            "name": r.name,
            "hsn_sac": r.hsn,
            "unit": r.unit,
            "brand": r.brand,
            "category": r.category,
            "default_price": r.default_price,
            "default_gst_rate": r.default_gst_rate,
            "available_stock": r.available_stock
        } for r in results
    ]

@router.post("/sale")
def complete_sale(
    request: Request,
    payload: PosCheckoutRequest, 
    company_id: int = Depends(get_bkr_company_id), 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user),
    commit: bool = True
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    if payload.idempotency_key:
        existing_sale = db.query(Sale).filter(Sale.idempotency_key == payload.idempotency_key, Sale.company_id == company_id).first()
        if existing_sale:
            return {
                "message": "Sale processed successfully (Idempotent response)",
                "receipt": {
                    "id": existing_sale.id,
                    "bill_number": existing_sale.bill_number,
                    "grand_total": existing_sale.grand_total,
                    "status": existing_sale.status
                }
            }

    if payload.origin_warehouse_id:
        default_warehouse = db.query(Warehouse).filter(Warehouse.id == payload.origin_warehouse_id).first()
        if not default_warehouse:
            raise HTTPException(status_code=400, detail="Origin warehouse not found")
    else:
        default_warehouse = _resolve_default_warehouse(db, company_id)

    try:
        # 1. Validate Stock (Aggregated to prevent overselling on duplicate items)
        if not payload.skip_inventory_update:
            required_quantities = {}
            for item in payload.items:
                required_quantities[item.product_id] = required_quantities.get(item.product_id, 0) + item.quantity

            for product_id, total_qty in required_quantities.items():
                inv = db.query(Inventory).filter(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == default_warehouse.id,
                    Inventory.company_id == company_id
                ).with_for_update().first() # Lock row

                if not inv or inv.available_qty < total_qty:
                    product = db.query(Product).filter(Product.id == product_id).first()
                    sku_name = product.sku if product else str(product_id)
                    raise HTTPException(status_code=400, detail=f"Insufficient Stock for SKU: {sku_name}")

        # 2. Generate Bill Number (company-aware)
        company = db.query(Company).filter(Company.id == company_id).first()
        company_code = company.code if company else "CO"
        bill_number = _generate_bill_number(company_code)

        # 2.1 Generate Invoice Number (sequence-based)
        from app.services.document_number_service import DocumentNumberService
        from app.models.schema import DocumentTypeEnum
        from app.services.invoice_number_service import _get_fiscal_year_string
        from datetime import datetime
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if payload.custom_invoice_number:
            invoice_number = payload.custom_invoice_number
        else:
            fy = _get_fiscal_year_string(datetime.today().date())
            invoice_number = DocumentNumberService.generate_number(
                db=db,
                company_id=company_id,
                document_type=DocumentTypeEnum.SALE,
                fiscal_year=fy,
                prefix_override=payload.invoice_prefix or (company.code if company else "CO")
            )

        # Company snapshot source (settings)
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()

        # 3. Create Sale
        sale = Sale(
            bill_number=bill_number,
            company_id=company_id,
            customer_name=payload.customer_name,
            customer_gstin=payload.customer_gstin,
            customer_address=payload.customer_address,
            customer_state=payload.customer_state,
            customer_state_code=payload.customer_state_code,
            customer_phone=payload.customer_phone,
            customer_mobile=payload.customer_mobile,
            created_at=payload.custom_invoice_date or datetime.utcnow(),
            sale_date=payload.custom_invoice_date or datetime.utcnow(),
            customer_email=payload.customer_email,
            place_of_supply=payload.place_of_supply,
            shipping_name=payload.shipping_name,
            shipping_address=payload.shipping_address,
            shipping_state=payload.shipping_state,
            shipping_state_code=payload.shipping_state_code,
            shipping_gstin=payload.shipping_gstin,
            idempotency_key=payload.idempotency_key,
            invoice_number=invoice_number,
            invoice_type=payload.invoice_type,
            vehicle_number=payload.vehicle_number,
            lr_rr_number=payload.lr_rr_number,
            terms_of_delivery=payload.terms_of_delivery,
            delivery_note=payload.delivery_note,
            delivery_note_date=payload.delivery_note_date,
            dispatch_document_number=payload.dispatch_document_number,
            dispatch_through=payload.dispatch_through,

            company_name_snapshot=(settings.legal_name if settings and settings.legal_name else (company.name if company else None)),
            company_gstin_snapshot=(settings.gstin if settings else None),
            company_address_snapshot=(settings.address if settings else None),
            company_state_snapshot=(settings.state if settings else None),
            company_state_code_snapshot=(settings.state_code if settings else None),
            company_email_snapshot=(settings.email if settings else None),
            company_phone_snapshot=(settings.phone if settings else None),
            company_logo_url_snapshot=(settings.logo_url if settings else None),
            company_bank_details_snapshot=(settings.bank_details if settings else None),

            tally_sync_status="NOT_APPLICABLE",  # updated below for B2B+enabled
            total_taxable_amount=payload.total_taxable_amount,
            total_tax=payload.total_tax,
            grand_total=payload.grand_total,
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
            payment_date=payload.payment_date,
            status="Completed"
        )
        db.add(sale)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing_sale = db.query(Sale).filter(Sale.idempotency_key == payload.idempotency_key, Sale.company_id == company_id).first()
            if existing_sale:
                return {
                    "message": "Sale processed successfully (Idempotent response)",
                    "receipt": {
                        "id": existing_sale.id,
                        "bill_number": existing_sale.bill_number,
                        "grand_total": existing_sale.grand_total,
                        "status": existing_sale.status
                    }
                }
            raise

        # 4. Create Sale Items and Deduct Inventory
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id, Product.company_id == company_id).first()
            final_hsn = item.hsn_sac or (product.hsn if product else None)
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item.product_id,
                sku=item.sku,
                quantity=item.quantity,
                selling_price=item.selling_price,
                gst_rate=item.gst_rate,
                taxable_amount=item.taxable_amount,
                cgst=item.cgst,
                sgst=item.sgst,
                igst=item.igst,
                line_total=item.line_total,
                discount=item.discount,
                product_name=item.product_name or (product.name if product else None),
                hsn_sac=final_hsn,
                unit=item.unit or (product.unit if product else None),
            )
            db.add(sale_item)

            # Auto-update product HSN if it was missing in DB and provided in POS
            if product and item.hsn_sac and (not product.hsn or product.hsn in ['0', 'N/A', '']):
                product.hsn = item.hsn_sac
            
            # 5. Inventory Deduction via Event Engine
            # Use the verified DB product SKU, not the client-supplied SKU
            # Deduct from Inventory using Event Engine (if not skipped)
            if not payload.skip_inventory_update and product:
                InventoryEventEngine.process_event(
                    db=db,
                    company_id=company_id,product_sku=product.sku,
                    warehouse_id=default_warehouse.id,
                    quantity=item.quantity,
                    event_type="SALE",
                    source="OFFLINE_POS",
                    reference_id=bill_number,
                    metadata_payload={"sale_id": sale.id}
                )

        if commit:
            db.commit()
            db.refresh(sale)
        else:
            db.flush()

        # Audit: invoice created (we treat Sale as invoice carrier for now)
        AuditLogService.log(
            db,
            company_id=company_id,
            entity_type="Sale",
            entity_id=sale.id,
            event_type="INVOICE_CREATED",
            message="Invoice created from POS checkout",
            metadata={"invoice_number": sale.invoice_number, "invoice_type": sale.invoice_type},
        )
        if commit:
            db.commit()
        else:
            db.flush()
        
        # Tally sync (B2B only, configurable) - runs AFTER sale is committed
        # Tally failures should NOT rollback the sale
        tally_result = {"status": sale.tally_sync_status}
        if sale.invoice_type == "B2B":
            try:
                import logging
                tally_logger = logging.getLogger("pos.tally")
                if TallyIntegrationService.is_enabled_for_company(db, company_id):
                    # Only attempt Tally Sync if we are actually committing
                    if commit:
                        res = TallyIntegrationService.sync_sale(db, sale_id=sale.id, mode="PROCESSING")
                        db.commit()
                        db.refresh(sale)
                        tally_result = {"status": res.status, "reference": res.reference, "error_message": res.error_message}
                    else:
                        sale.tally_sync_status = "PENDING"  # Will be synced later
                        db.flush()
                        tally_result = {"status": "PENDING"}
                else:
                    sale.tally_sync_status = "NOT_APPLICABLE"
                    if commit:
                        db.commit()
                        db.refresh(sale)
                    else:
                        db.flush()
            except Exception as tally_err:
                import logging
                logging.getLogger(__name__).error(str(tally_err), exc_info=True)
                tally_logger.error(f"Tally sync failed for sale {sale.id}: {tally_err}")
                sale.tally_sync_status = "FAILED"
                if commit:
                    db.commit()
                    db.refresh(sale)
                else:
                    db.flush()
                tally_result = {"status": "FAILED", "error_message": str(tally_err)}

        # Add audit logs
        AuditLogService.log(
            db, 
            company_id=company_id,entity_type="POS Checkout", 
            entity_id=sale.id, 
            event_type="Sale",
            message=f"POS Checkout by User {user.id}",
            metadata={"total_amount": sale.grand_total, "invoice_number": sale.invoice_number}
        )

        logger.info(f"Action: Sale | User: {user.id} | Company: {company_id} | Status: Success | SaleID: {sale.id} | Value: {sale.grand_total}")
        log_metric("sale_completed", 1, {"company_id": company_id})

        receipt = _build_invoice_dto(sale)
        return {"message": "Sale completed successfully", "receipt": receipt, "tally_sync": tally_result}
        
    except HTTPException:
        if commit:
            db.rollback()
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        if commit:
            db.rollback()
        raise HTTPException(status_code=500, detail="An internal error occurred while processing the sale.")

@router.get("/history")
def get_sales_history(
    skip: int = 0, 
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    invoice_type: Optional[str] = None,
    tally_status: Optional[str] = None,
    invoice_number: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    return_status: Optional[str] = None, # None, "Partially Returned", "Fully Returned", "Active Sales"
    company_id: int = Depends(get_bkr_company_id), 
    db: Session = Depends(get_db)
):
    # Subqueries for sold and returned totals
    sold_subq = (
        db.query(
            SaleItem.sale_id,
            func.sum(SaleItem.quantity).label("total_sold")
        )
        .group_by(SaleItem.sale_id)
        .subquery()
    )

    returned_subq = (
        db.query(
            SalesReturn.sale_id,
            func.sum(SalesReturnItem.returned_quantity).label("total_returned")
        )
        .join(SalesReturnItem, SalesReturn.id == SalesReturnItem.return_id)
        .filter(SalesReturn.status == "Completed")
        .group_by(SalesReturn.sale_id)
        .subquery()
    )

    query = db.query(
        Sale,
        func.coalesce(sold_subq.c.total_sold, 0).label("total_sold"),
        func.coalesce(returned_subq.c.total_returned, 0).label("total_returned")
    ).outerjoin(sold_subq, Sale.id == sold_subq.c.sale_id) \
     .outerjoin(returned_subq, Sale.id == returned_subq.c.sale_id) \
     .filter(Sale.company_id == company_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Sale.bill_number.ilike(search_term)) |
            (Sale.customer_name.ilike(search_term)) |
            (Sale.customer_mobile.ilike(search_term)) |
            (Sale.invoice_number.ilike(search_term))
        )
        
    if status:
        query = query.filter(Sale.status == status)

    if invoice_type:
        query = query.filter(Sale.invoice_type == invoice_type.upper())

    if tally_status:
        query = query.filter(Sale.tally_sync_status == tally_status.upper())

    if invoice_number:
        query = query.filter(Sale.invoice_number.ilike(f"%{invoice_number}%"))

    if date_from:
        try:
            from datetime import datetime as dt
            query = query.filter(Sale.sale_date >= dt.fromisoformat(date_from))
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime as dt
            query = query.filter(Sale.sale_date <= dt.fromisoformat(date_to))
        except ValueError:
            pass
            
    if return_status:
        # Note: the label names from subqueries can be referenced directly using their column objects
        total_sold_col = func.coalesce(sold_subq.c.total_sold, 0)
        total_returned_col = func.coalesce(returned_subq.c.total_returned, 0)
        
        if return_status == "None":
            query = query.filter(total_returned_col == 0)
        elif return_status == "Partially Returned":
            query = query.filter((total_returned_col > 0) & (total_returned_col < total_sold_col))
        elif return_status == "Fully Returned":
            query = query.filter((total_returned_col > 0) & (total_returned_col >= total_sold_col))
        elif return_status == "Active Sales":
            query = query.filter(total_returned_col < total_sold_col)
        
    total = query.count()
    results = query.order_by(Sale.id.desc()).offset(skip).limit(limit).all()
    
    response_items = []
    for row in results:
        s = row.Sale
        t_sold = row.total_sold
        t_ret = row.total_returned
        net_qty = t_sold - t_ret
        
        computed_return_status = "None"
        if t_ret > 0:
            computed_return_status = "Fully Returned" if t_ret >= t_sold else "Partially Returned"
            
        # Get linked return ids efficiently without N+1 if needed, but since it's just a boolean/id list, 
        # we can lazily load or omit if not strictly required for the list view (or query separately)
        # We will query linked return ids for this page
        
        response_items.append({
            "id": s.id,
            "bill_number": s.bill_number,
            "invoice_number": s.invoice_number,
            "invoice_type": s.invoice_type,
            "tally_sync_status": s.tally_sync_status,
            "customer_name": s.customer_name,
            "customer_gstin": s.customer_gstin,
            "sale_date": s.sale_date,
            "grand_total": s.grand_total,
            "total_tax": s.total_tax,
            "payment_method": s.payment_method,
            "status": s.status,
            "items_count": len(s.items),
            "return_status": computed_return_status,
            "returned_quantity": t_ret,
            "remaining_quantity": net_qty,
            "total_sold": t_sold
        })
    
    # Enrich with linked return ids
    if response_items:
        sale_ids = [item["id"] for item in response_items]
        linked_returns = db.query(SalesReturn.id, SalesReturn.sale_id).filter(SalesReturn.sale_id.in_(sale_ids)).all()
        return_map = {}
        for ret_id, s_id in linked_returns:
            if s_id not in return_map:
                return_map[s_id] = []
            return_map[s_id].append(ret_id)
            
        for item in response_items:
            item["linked_sales_return_ids"] = return_map.get(item["id"], [])
    
    return {
        "total": total,
        "items": response_items
    }


def _build_invoice_dto(sale: Sale, db: Session = None) -> dict:
    # Fetch returns data if db is provided
    returns_summary = []
    item_return_map = {}
    
    if db:
        returns = db.query(SalesReturn).filter(SalesReturn.sale_id == sale.id, SalesReturn.status != "Cancelled").all()
        for r in returns:
            # sum up returned items
            ret_qty = sum(ri.returned_quantity for ri in r.items)
            returns_summary.append({
                "id": r.id,
                "return_number": r.return_number,
                "date": r.return_date.isoformat() if r.return_date else None,
                "status": r.status,
                "returned_quantity": ret_qty
            })
            
            # Map item level returns for "Completed" returns
            if r.status == "Completed":
                for ri in r.items:
                    if ri.sale_item_id:
                        item_return_map[ri.sale_item_id] = item_return_map.get(ri.sale_item_id, 0) + ri.returned_quantity
                        
    dto_items = []
    for i in (sale.items or []):
        ret_qty = item_return_map.get(i.id, 0)
        net_qty = i.quantity - ret_qty
        
        item_status = "Sold"
        if ret_qty > 0:
            item_status = "Returned" if ret_qty >= i.quantity else "Partial"
            
        dto_items.append({
            "id": i.id,
            "sku": i.sku,
            "product_name": i.product_name or (i.product.name if i.product else None),
            "hsn_sac": i.hsn_sac,
            "gst_rate": i.gst_rate,
            "quantity": i.quantity, # original sold
            "returned_quantity": ret_qty,
            "remaining_quantity": net_qty,
            "item_status": item_status,
            "unit": i.unit,
            "rate": i.selling_price,
            "discount": i.discount,
            "taxable_value": i.taxable_amount,
            "cgst": i.cgst,
            "sgst": i.sgst,
            "igst": i.igst,
            "line_total": i.line_total,
        })

    return {
        "id": sale.id,
        "status": sale.status,
        "bill_number": sale.bill_number,
        "invoice_number": sale.invoice_number,
        "invoice_type": sale.invoice_type,
        "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
        "payment_method": sale.payment_method,
        "payment_reference": sale.payment_reference,
        "payment_date": sale.payment_date.isoformat() if sale.payment_date else None,
        "payment_terms": sale.payment_terms,
        "delivery_note": sale.delivery_note,
        "delivery_note_date": sale.delivery_note_date.isoformat() if sale.delivery_note_date else None,
        "dispatch_document_number": sale.dispatch_document_number,
        "dispatch_through": sale.dispatch_through,
        "destination": sale.destination,
        "vehicle_number": sale.vehicle_number,
        "lr_rr_number": sale.lr_rr_number,
        "terms_of_delivery": sale.terms_of_delivery,
        "company": {
            "name": sale.company_name_snapshot,
            "gstin": sale.company_gstin_snapshot,
            "address": sale.company_address_snapshot,
            "state": sale.company_state_snapshot,
            "state_code": sale.company_state_code_snapshot,
            "email": sale.company_email_snapshot,
            "phone": sale.company_phone_snapshot,
            "logo_url": sale.company_logo_url_snapshot,
            "bank_details": sale.company_bank_details_snapshot,
        },
        "customer": {
            "name": sale.customer_name,
            "gstin": sale.customer_gstin,
            "address": sale.customer_address,
            "state": sale.customer_state,
            "state_code": sale.customer_state_code,
            "place_of_supply": sale.place_of_supply,
            "email": sale.customer_email,
            "phone": sale.customer_phone,
            "mobile": sale.customer_mobile,
        },
        "shipping": {
            "name": sale.shipping_name,
            "gstin": sale.shipping_gstin,
            "address": sale.shipping_address,
            "state": sale.shipping_state,
            "state_code": sale.shipping_state_code,
        } if sale.shipping_name else None,
        "totals": {
            "taxable_amount": sale.total_taxable_amount,
            "total_tax": sale.total_tax,
            "grand_total": sale.grand_total,
        },
        "tally": {
            "status": sale.tally_sync_status,
            "synced_at": sale.tally_sync_at.isoformat() if sale.tally_sync_at else None,
            "reference": sale.tally_reference,
            "error_message": sale.tally_error_message,
        },
        "items": dto_items,
        "related_returns": returns_summary
    }


@router.get("/sales/{sale_id}")
def get_sale_invoice(sale_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    if sale.company_id != company_id:
        transfer = db.query(StockTransfer).filter(StockTransfer.invoice_id == sale_id).first()
        if not transfer or (transfer.from_company_id != company_id and transfer.to_company_id != company_id):
            raise HTTPException(status_code=404, detail="Sale not found")
            
    return {"receipt": _build_invoice_dto(sale, db)}


@router.get("/invoice/{invoice_number}")
def get_invoice_by_number(invoice_number: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(
        Sale.invoice_number == invoice_number,
        Sale.company_id == company_id
    ).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return {"receipt": _build_invoice_dto(sale, db)}


@router.post("/sales/{sale_id}/retry-tally")
def retry_tally_sync(sale_id: int, company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if (sale.invoice_type or "B2C") != "B2B":
        raise HTTPException(status_code=400, detail="Tally sync is only applicable for B2B invoices")

    if not TallyIntegrationService.is_enabled_for_company(db, company_id):
        raise HTTPException(status_code=400, detail="Tally integration is disabled for this company")

    sale.tally_sync_status = "RETRYING"
    db.commit()

    res = TallyIntegrationService.sync_sale(db, sale_id=sale.id, mode="PROCESSING")
    db.commit()
    db.refresh(sale)
    return {"tally_sync": {"status": res.status, "reference": res.reference, "error_message": res.error_message}, "receipt": _build_invoice_dto(sale, db)}

@router.get("/sales/{sale_id}/tally-payload")
def get_tally_payload(sale_id: int, company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    try:
        import json
        json_payload = TallyPayloadBuilder.build_json(sale)
        xml_payload = TallyPayloadBuilder.build_xml(sale)
        
        return {
            "json": json.dumps(json_payload, indent=2),
            "xml": xml_payload
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while generating the export.")


# =============================================================================
# OFFLINE POS QUEUE ENDPOINTS
# =============================================================================

from app.models.schema import OfflineSale

class OfflineSaleSubmitRequest(BaseModel):
    idempotency_key: str
    payload: dict

@router.post("/offline/submit")
def submit_offline_sale(
    data: OfflineSaleSubmitRequest,
    company_id: int = Depends(get_pos_company_id),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store a single offline sale in the queue for later sync."""
    # Idempotency check
    existing = db.query(OfflineSale).filter(OfflineSale.idempotency_key == data.idempotency_key).first()
    if existing:
        return {"message": "Already queued (idempotent)", "offline_sale_id": existing.id, "status": existing.status}

    offline = OfflineSale(
        company_id=company_id,
        operator_id=user.id,
        payload=data.payload,
        status="PENDING",
        idempotency_key=data.idempotency_key
    )
    db.add(offline)
    db.commit()
    db.refresh(offline)

    logger.info(f"Offline sale queued: id={offline.id} company={company_id} user={user.id}")
    return {"message": "Offline sale queued", "offline_sale_id": offline.id, "status": "PENDING"}


@router.get("/offline/pending")
def list_pending_offline_sales(
    company_id: int = Depends(get_pos_company_id),
    db: Session = Depends(get_db)
):
    """List all PENDING offline sales for the current company."""
    pending = db.query(OfflineSale).filter(
        OfflineSale.company_id == company_id,
        OfflineSale.status == "PENDING"
    ).order_by(OfflineSale.created_at.asc()).all()

    return [
        {
            "id": p.id,
            "idempotency_key": p.idempotency_key,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "status": p.status,
            "payload_summary": {
                "items_count": len(p.payload.get("items", [])) if isinstance(p.payload, dict) else 0,
                "grand_total": p.payload.get("grand_total") if isinstance(p.payload, dict) else None
            }
        }
        for p in pending
    ]


@router.post("/offline/sync")
def sync_offline_sales(
    request: Request,
    company_id: int = Depends(get_pos_company_id),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process all PENDING offline sales for the current company. Uses existing sale logic with idempotency."""
    pending = db.query(OfflineSale).filter(
        OfflineSale.company_id == company_id,
        OfflineSale.status == "PENDING"
    ).order_by(OfflineSale.created_at.asc()).all()

    if not pending:
        return {"synced": 0, "failed": 0, "details": [], "message": "No pending offline sales"}

    synced = 0
    failed = 0
    details = []

    for item in pending:
        try:
            # Build PosCheckoutRequest from the stored payload
            checkout_payload = PosCheckoutRequest(**item.payload)
            # Use the offline sale's idempotency_key to prevent duplicates
            checkout_payload.idempotency_key = item.idempotency_key

            result = complete_sale(
                request=request,
                payload=checkout_payload,
                company_id=company_id,
                db=db,
                user=user,
                commit=False  # We commit once at the end
            )

            item.status = "SYNCED"
            item.synced_at = datetime.utcnow()
            if result and "receipt" in result:
                item.sale_id = result["receipt"].get("id")
            synced += 1
            details.append({"offline_id": item.id, "status": "SYNCED", "sale_id": item.sale_id})

        except Exception as e:
            item.status = "FAILED"
            item.error_message = str(e)[:500]
            failed += 1
            details.append({"offline_id": item.id, "status": "FAILED", "error": str(e)[:200]})
            logger.error(f"Offline sync failed for id={item.id}: {e}")

    db.commit()

    logger.info(f"Offline sync complete: company={company_id} synced={synced} failed={failed}")
    return {"synced": synced, "failed": failed, "details": details}

@router.post("/sales/{sale_id}/cancel")
def cancel_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == current_user.company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    if sale.status == 'Cancelled':
        raise HTTPException(status_code=400, detail="Sale is already cancelled")
        
    if sale.return_status and sale.return_status != 'None':
        raise HTTPException(status_code=400, detail="Cannot cancel a sale that has returns. Please process a full return instead.")

    # Find associated inventory movements
    movements = db.query(InventoryMovement).filter(
        InventoryMovement.reference_id == sale.bill_number,
        InventoryMovement.source == 'OFFLINE_POS'
    ).all()
    
    for mov in movements:
        # Revert inventory
        inv = db.query(Inventory).filter_by(
            product_id=mov.product_id,
            warehouse_id=mov.warehouse_id
        ).first()
        
        if inv:
            inv._allow_mutation = True
            inv.current_qty -= mov.qty_changed # Subtracting a negative deduction adds it back
            inv.available_qty = inv.current_qty - (inv.reserved_qty or 0)
            inv._allow_mutation = False
            
            # Log the cancellation movement
            new_mov = InventoryMovement(
                product_id=mov.product_id,
                warehouse_id=mov.warehouse_id,
                movement_type='IN',
                qty_changed=-mov.qty_changed,
                reference_id=sale.bill_number,
                source='SALE_CANCELLED',
                notes='Reverted due to sale cancellation'
            )
            db.add(new_mov)
            
    sale.status = 'Cancelled'
    
    # Add audit log
    log = AuditLog(
        user_id=current_user.id,
        company_id=current_user.company_id,
        action="CANCEL",
        entity_type="Sale",
        entity_id=sale.id,
        details=f"Cancelled sale {sale.bill_number} and reverted inventory"
    )
    db.add(log)
    
    db.commit()
    return {"message": "Sale cancelled successfully", "sale_id": sale.id, "status": "Cancelled"}

@router.put("/sales/{sale_id}")
def update_sale(
    sale_id: int,
    payload: PosCheckoutRequest,
    company_id: int = Depends(get_bkr_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.services.inventory_event_engine import InventoryEventEngine
    
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    if sale.status == 'Cancelled':
        raise HTTPException(status_code=400, detail="Cannot edit a cancelled sale")
        
    # Validation: Ensure no returns exist
    active_returns = db.query(SalesReturn).filter(SalesReturn.sale_id == sale.id, SalesReturn.status != 'Cancelled').all()
    if active_returns:
        raise HTTPException(status_code=400, detail="Cannot edit a sale that has active sales returns. Please cancel the returns first.")

    # 1. Header Updates
    sale.customer_name = payload.customer_name
    sale.customer_gstin = payload.customer_gstin
    sale.customer_address = payload.customer_address
    sale.customer_state = payload.customer_state
    sale.customer_state_code = payload.customer_state_code
    sale.customer_phone = payload.customer_phone
    sale.customer_mobile = payload.customer_mobile
    sale.customer_email = payload.customer_email
    sale.place_of_supply = payload.place_of_supply
    sale.shipping_name = payload.shipping_name
    sale.shipping_address = payload.shipping_address
    sale.shipping_state = payload.shipping_state
    sale.shipping_state_code = payload.shipping_state_code
    sale.shipping_gstin = payload.shipping_gstin
    sale.invoice_type = payload.invoice_type
    
    if payload.custom_invoice_date:
        sale.created_at = payload.custom_invoice_date
        sale.sale_date = payload.custom_invoice_date
        
    sale.vehicle_number = payload.vehicle_number
    sale.lr_rr_number = payload.lr_rr_number
    sale.terms_of_delivery = payload.terms_of_delivery
    sale.delivery_note = payload.delivery_note
    sale.delivery_note_date = payload.delivery_note_date
    sale.dispatch_document_number = payload.dispatch_document_number
    sale.dispatch_through = payload.dispatch_through
    
    sale.total_taxable_amount = payload.total_taxable_amount
    sale.total_tax = payload.total_tax
    sale.grand_total = payload.grand_total
    
    # Reset Tally sync
    if sale.tally_sync_status in ['COMPLETED', 'FAILED', 'PENDING']:
        sale.tally_sync_status = 'PENDING'
        
    # 2. Resolve default warehouse for delta tracking
    if payload.origin_warehouse_id:
        default_warehouse = db.query(Warehouse).filter(Warehouse.id == payload.origin_warehouse_id).first()
    else:
        default_warehouse = _resolve_default_warehouse(db, company_id)
        
    if not default_warehouse:
        raise HTTPException(status_code=400, detail="Warehouse not found for delta processing")

    # 3. Item Delta Calculation
    old_items = {item.id: item for item in sale.items}
    new_items_payload = payload.items or []
    
    # Process updates and additions
    for req_item in new_items_payload:
        product = db.query(Product).filter(Product.id == req_item.product_id).first()
        if not product:
            continue
            
        # Is it an existing item that came back from the UI? 
        # (Assuming the UI passes back the sale_item.id if it existed, we need a way to match them. 
        # If UI doesn't have sale_item.id, we map by SKU)
        existing_item = next((oi for oi in old_items.values() if oi.sku == (req_item.product_sku or product.sku)), None)
        
        delta_qty = req_item.quantity
        if existing_item:
            delta_qty = req_item.quantity - existing_item.quantity
            
            # Update existing row
            existing_item.quantity = req_item.quantity
            existing_item.selling_price = req_item.selling_price
            existing_item.gst_rate = req_item.gst_rate
            existing_item.taxable_amount = req_item.taxable_amount
            existing_item.cgst = req_item.cgst
            existing_item.sgst = req_item.sgst
            existing_item.igst = req_item.igst
            existing_item.line_total = req_item.line_total
            existing_item.product_name = req_item.product_name or product.name
            existing_item.hsn_sac = req_item.hsn_sac or product.hsn
            existing_item.unit = product.unit
            existing_item.discount = req_item.discount or 0.0
            
            del old_items[existing_item.id] # mark as processed
        else:
            # Create new row
            new_sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                sku=product.sku,
                quantity=req_item.quantity,
                selling_price=req_item.selling_price,
                gst_rate=req_item.gst_rate,
                taxable_amount=req_item.taxable_amount,
                cgst=req_item.cgst,
                sgst=req_item.sgst,
                igst=req_item.igst,
                line_total=req_item.line_total,
                product_name=req_item.product_name or product.name,
                hsn_sac=req_item.hsn_sac or product.hsn,
                unit=product.unit,
                discount=req_item.discount or 0.0
            )
            db.add(new_sale_item)
            
        # Apply Inventory Delta
        if delta_qty != 0 and not payload.skip_inventory_update:
            event_type = "SALE" if delta_qty > 0 else "ADD"
            source = "OFFLINE_POS" if delta_qty > 0 else "INVOICE_EDIT"
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=product.sku,
                warehouse_id=default_warehouse.id,
                quantity=abs(delta_qty),
                event_type=event_type,
                source=source,
                reference_id=sale.bill_number,
                metadata_payload={"sale_id": sale.id, "edit_delta": delta_qty},
                
            )
            
    # Process removals (anything left in old_items was deleted from the UI)
    for oi in old_items.values():
        if not payload.skip_inventory_update:
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=oi.sku,
                warehouse_id=default_warehouse.id,
                quantity=oi.quantity,
                event_type="ADD",
                source="INVOICE_EDIT",
                reference_id=sale.bill_number,
                metadata_payload={"sale_id": sale.id, "edit_delta": -oi.quantity},
                
            )
        db.delete(oi)

    db.commit()
    return {"message": "Invoice updated successfully"}
