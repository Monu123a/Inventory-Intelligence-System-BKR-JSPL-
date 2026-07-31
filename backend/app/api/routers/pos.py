from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4

from app.models.db import get_db
from app.models.schema import Company, Product, Warehouse, Inventory, Sale, SaleItem, CompanySettings
from app.api.dependencies import get_current_company_id
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.invoice_number_service import InvoiceNumberService
from app.services.tally_integration_service import TallyIntegrationService
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/pos", tags=["POS"])

# --- Authorization Dependency ---
def get_bkr_company_id(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)) -> int:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company or company.code != "BKR":
        raise HTTPException(status_code=403, detail="Offline POS is strictly restricted to BKR.")
    return company_id


def _resolve_default_bkr_warehouse(db: Session, company_id: int) -> Warehouse:
    warehouses = db.query(Warehouse).filter(
        Warehouse.company_id == company_id,
        Warehouse.status == "Active"
    ).order_by(Warehouse.id.asc()).all()

    if not warehouses:
        raise HTTPException(status_code=400, detail="No active warehouse configured for BKR")

    if len(warehouses) == 1:
        return warehouses[0]

    preferred_codes = {"DEFAULT", "BKR-DEFAULT", "BKR_DEFAULT", "MAIN", "POS"}
    for warehouse in warehouses:
        code = (warehouse.code or "").strip().upper()
        name = (warehouse.name or "").strip().lower()
        if code in preferred_codes or "default" in name or "main" in name or "pos" in name:
            return warehouse

    raise HTTPException(
        status_code=400,
        detail="Multiple active BKR warehouses found. Mark one clearly as the default warehouse before using POS."
    )


def _generate_bill_number() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S%f")
    suffix = uuid4().hex[:6].upper()
    return f"BKR-{timestamp}-{suffix}"

# --- Pydantic Models ---
class PosCartItem(BaseModel):
    product_id: int
    sku: str
    product_name: Optional[str] = None
    hsn_sac: Optional[str] = None
    unit: Optional[str] = None
    quantity: int
    selling_price: float
    discount: float = 0.0
    gst_rate: float
    taxable_amount: float
    cgst: float
    sgst: float
    igst: float = 0.0
    line_total: float

class PosCheckoutRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_gstin: Optional[str] = None
    customer_address: Optional[str] = None
    customer_state: Optional[str] = None
    customer_state_code: Optional[str] = None
    place_of_supply: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

    invoice_type: str = "B2C"  # B2C | B2B
    payment_terms: Optional[str] = None
    delivery_note: Optional[str] = None
    delivery_note_date: Optional[datetime] = None
    dispatch_document_number: Optional[str] = None
    dispatch_through: Optional[str] = None
    destination: Optional[str] = None
    vehicle_number: Optional[str] = None
    lr_rr_number: Optional[str] = None
    terms_of_delivery: Optional[str] = None

    payment_method: str
    payment_reference: Optional[str] = None
    payment_date: Optional[datetime] = None
    total_taxable_amount: float
    total_tax: float
    grand_total: float
    items: List[PosCartItem]

# --- Endpoints ---

@router.get("/products/search")
def search_products(q: str = "", company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    if not q or len(q) < 2:
        return []

    search_term = f"%{q}%"
    
    # We need available stock from the default BKR warehouse
    # Wait, requirement: "All offline POS sales should automatically deduct inventory from the default BKR warehouse."
    default_warehouse = _resolve_default_bkr_warehouse(db, company_id)

    results = db.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.hsn_code,
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
            "hsn_sac": r.hsn_code,
            "unit": r.unit,
            "brand": r.brand,
            "category": r.category,
            "default_price": r.default_price,
            "default_gst_rate": r.default_gst_rate,
            "available_stock": r.available_stock
        } for r in results
    ]

@router.post("/sale")
def complete_sale(request: PosCheckoutRequest, company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    if not request.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    default_warehouse = _resolve_default_bkr_warehouse(db, company_id)

    try:
        # 1. Validate Stock
        for item in request.items:
            inv = db.query(Inventory).filter(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == default_warehouse.id
            ).with_for_update().first() # Lock row

            if not inv or inv.available_qty < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient Stock for SKU: {item.sku}")

        # 2. Generate Bill Number
        bill_number = _generate_bill_number()

        # 2.1 Generate Invoice Number (sequence-based)
        company = db.query(Company).filter(Company.id == company_id).first()
        invoice_number = InvoiceNumberService.generate_next(
            db,
            company_id=company_id,
            company_code=(company.code if company else "CO"),
        )

        # Company snapshot source (settings)
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()

        # 3. Create Sale
        sale = Sale(
            bill_number=bill_number,
            company_id=company_id,
            invoice_number=invoice_number,
            invoice_type=(request.invoice_type or "B2C").strip().upper(),
            customer_name=request.customer_name,
            customer_mobile=request.customer_mobile,
            customer_gstin=request.customer_gstin,
            customer_address=request.customer_address,
            customer_state=request.customer_state,
            customer_state_code=request.customer_state_code,
            place_of_supply=request.place_of_supply,
            customer_email=request.customer_email,
            customer_phone=request.customer_phone,

            payment_terms=request.payment_terms,
            delivery_note=request.delivery_note,
            delivery_note_date=request.delivery_note_date,
            dispatch_document_number=request.dispatch_document_number,
            dispatch_through=request.dispatch_through,
            destination=request.destination,
            vehicle_number=request.vehicle_number,
            lr_rr_number=request.lr_rr_number,
            terms_of_delivery=request.terms_of_delivery,

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
            total_taxable_amount=request.total_taxable_amount,
            total_tax=request.total_tax,
            grand_total=request.grand_total,
            payment_method=request.payment_method,
            payment_reference=request.payment_reference,
            payment_date=request.payment_date,
            status="Completed"
        )
        db.add(sale)
        db.flush()

        # 4. Create Sale Items and Deduct Inventory
        for item in request.items:
            product = db.query(Product).filter(Product.id == item.product_id, Product.company_id == company_id).first()
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
                hsn_sac=item.hsn_sac or (product.hsn_code if product else None),
                unit=item.unit or (product.unit if product else None),
            )
            db.add(sale_item)
            
            # 5. Inventory Deduction via Event Engine
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=item.sku,
                warehouse_id=default_warehouse.id,
                quantity=item.quantity,
                event_type="SALE",
                source="OFFLINE_POS",
                reference_id=bill_number,
                metadata_payload={"sale_id": sale.id}
            )

        db.commit()
        db.refresh(sale)

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
        db.commit()
        
        # Format Receipt Data
        # Tally sync (B2B only, configurable)
        tally_result = {"status": sale.tally_sync_status}
        if sale.invoice_type == "B2B":
            if TallyIntegrationService.is_enabled_for_company(db, company_id):
                res = TallyIntegrationService.sync_sale(db, sale_id=sale.id, mode="PROCESSING")
                db.commit()
                db.refresh(sale)
                tally_result = {"status": res.status, "reference": res.reference, "error_message": res.error_message}
            else:
                sale.tally_sync_status = "NOT_APPLICABLE"
                db.commit()
                db.refresh(sale)

        receipt = _build_invoice_dto(sale)
        return {"message": "Sale completed successfully", "receipt": receipt, "tally_sync": tally_result}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
    company_id: int = Depends(get_bkr_company_id), 
    db: Session = Depends(get_db)
):
    query = db.query(Sale).filter(Sale.company_id == company_id)
    
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
        
    total = query.count()
    sales = query.order_by(Sale.id.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [
            {
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
                "items_count": len(s.items)
            } for s in sales
        ]
    }


def _build_invoice_dto(sale: Sale) -> dict:
    return {
        "id": sale.id,
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
        },
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
        "items": [
            {
                "sku": i.sku,
                "product_name": i.product_name or (i.product.name if i.product else None),
                "hsn_sac": i.hsn_sac,
                "gst_rate": i.gst_rate,
                "quantity": i.quantity,
                "unit": i.unit,
                "rate": i.selling_price,
                "discount": i.discount,
                "taxable_value": i.taxable_amount,
                "cgst": i.cgst,
                "sgst": i.sgst,
                "igst": i.igst,
                "line_total": i.line_total,
            }
            for i in (sale.items or [])
        ],
    }


@router.get("/sales/{sale_id}")
def get_sale_invoice(sale_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return {"receipt": _build_invoice_dto(sale)}


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
    return {"tally_sync": {"status": res.status, "reference": res.reference, "error_message": res.error_message}, "receipt": _build_invoice_dto(sale)}

@router.get("/sales/{sale_id}/tally-payload")
def get_tally_payload(sale_id: int, company_id: int = Depends(get_bkr_company_id), db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    try:
        from app.services.tally_payload_builder import TallyPayloadBuilder
        import json
        json_payload = TallyPayloadBuilder.build_json(sale)
        xml_payload = TallyPayloadBuilder.build_xml(sale)
        
        return {
            "json": json.dumps(json_payload, indent=2),
            "xml": xml_payload
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
