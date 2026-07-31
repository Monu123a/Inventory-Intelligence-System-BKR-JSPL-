from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4

from app.models.db import get_db
from app.models.schema import Company, Product, Warehouse, Inventory, Sale, SaleItem
from app.api.dependencies import get_current_company_id
from app.services.inventory_event_engine import InventoryEventEngine

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
    quantity: int
    selling_price: float
    gst_rate: float
    taxable_amount: float
    cgst: float
    sgst: float
    line_total: float

class PosCheckoutRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    payment_method: str
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

        # 3. Create Sale
        sale = Sale(
            bill_number=bill_number,
            company_id=company_id,
            customer_name=request.customer_name,
            customer_mobile=request.customer_mobile,
            total_taxable_amount=request.total_taxable_amount,
            total_tax=request.total_tax,
            grand_total=request.grand_total,
            payment_method=request.payment_method,
            status="Completed"
        )
        db.add(sale)
        db.flush()

        # 4. Create Sale Items and Deduct Inventory
        for item in request.items:
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
                line_total=item.line_total
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
        
        # Format Receipt Data
        receipt = {
            "bill_number": sale.bill_number,
            "sale_date": sale.sale_date.isoformat(),
            "customer_name": sale.customer_name,
            "payment_method": sale.payment_method,
            "total_taxable_amount": sale.total_taxable_amount,
            "total_tax": sale.total_tax,
            "grand_total": sale.grand_total,
            "items": [
                {
                    "sku": i.sku,
                    "product_name": i.product.name,
                    "quantity": i.quantity,
                    "selling_price": i.selling_price,
                    "gst_rate": i.gst_rate,
                    "line_total": i.line_total
                } for i in sale.items
            ]
        }
        return {"message": "Sale completed successfully", "receipt": receipt}
        
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
    company_id: int = Depends(get_bkr_company_id), 
    db: Session = Depends(get_db)
):
    query = db.query(Sale).filter(Sale.company_id == company_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Sale.bill_number.ilike(search_term)) |
            (Sale.customer_name.ilike(search_term)) |
            (Sale.customer_mobile.ilike(search_term))
        )
        
    if status:
        query = query.filter(Sale.status == status)
        
    total = query.count()
    sales = query.order_by(Sale.id.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [
            {
                "id": s.id,
                "bill_number": s.bill_number,
                "customer_name": s.customer_name,
                "sale_date": s.sale_date,
                "grand_total": s.grand_total,
                "payment_method": s.payment_method,
                "status": s.status,
                "items_count": len(s.items)
            } for s in sales
        ]
    }
