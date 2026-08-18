from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date
from typing import Optional

from app.models.db import get_db
from app.api.dependencies import get_current_user, get_current_company_id
from app.models.schema import (
    User, Sale, SaleItem, Inventory, Product, Warehouse,
    FCDispatch, FCReturn, DamageClaim, DefectiveInventory,
    StateHub
)

router = APIRouter(prefix="/business-reports", tags=["Business Reports"])


# ---------------------------------------------------------------------------
# 1. GET /sales - Paginated Sales Analytics grouped by Day / Week / Month
# ---------------------------------------------------------------------------
@router.get("/sales")
def get_sales_report(
    date_from: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    group_by: str = Query("day", pattern="^(day|week|month)$", description="Grouping dimension"),
    status: Optional[str] = Query(None, description="Sale status (e.g., Completed, Draft, Cancelled)"),
    search: Optional[str] = Query(None, description="Search by bill number, invoice number, customer name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated sales metrics grouped dynamically by day, week, or month.
    Avoids N+1 queries by aggregating directly in the database engine.
    """
    # Define date grouping field (SQLite compatible)
    if group_by == "month":
        period_col = func.strftime("%Y-%m", Sale.sale_date).label("period")
    elif group_by == "week":
        period_col = func.strftime("%Y-%W", Sale.sale_date).label("period")
    else:
        period_col = func.date(Sale.sale_date).label("period")

    # 1. Filter Sales First (No Joins)
    sale_base = db.query(
        Sale.id,
        period_col,
        Sale.total_taxable_amount,
        Sale.total_tax,
        Sale.grand_total
    ).filter(Sale.company_id == company_id)

    if date_from:
        sale_base = sale_base.filter(Sale.sale_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        sale_base = sale_base.filter(Sale.sale_date <= datetime.combine(date_to, datetime.max.time()))
    if status:
        sale_base = sale_base.filter(Sale.status == status)
    if search:
        search_pattern = f"%{search}%"
        sale_base = sale_base.filter(
            or_(
                Sale.bill_number.ilike(search_pattern),
                Sale.invoice_number.ilike(search_pattern),
                Sale.customer_name.ilike(search_pattern)
            )
        )

    sale_sq = sale_base.subquery()

    # 2. Base query for item aggregation
    item_sq = db.query(
        SaleItem.sale_id,
        func.sum(SaleItem.quantity).label("qty")
    ).group_by(SaleItem.sale_id).subquery()

    # 3. Aggregate safely over the subquery
    query = db.query(
        sale_sq.c.period,
        func.count(sale_sq.c.id).label("total_orders"),
        func.sum(func.coalesce(item_sq.c.qty, 0)).label("total_items_sold"),
        func.sum(sale_sq.c.total_taxable_amount).label("total_taxable_amount"),
        func.sum(sale_sq.c.total_tax).label("total_tax"),
        func.sum(sale_sq.c.grand_total).label("total_revenue")
    ).outerjoin(item_sq, item_sq.c.sale_id == sale_sq.c.id)\
     .group_by(sale_sq.c.period).order_by(sale_sq.c.period.desc())

    # Count total aggregated groups for pagination
    total_count = query.count()
    
    print(f"[REVENUE FIX] {company_id}, {total_count}")

    # Apply pagination
    skip = (page - 1) * limit
    results = query.offset(skip).limit(limit).all()

    items = [
        {
            "period": str(row.period),
            "total_orders": row.total_orders or 0,
            "total_items_sold": row.total_items_sold or 0,
            "total_taxable_amount": round(row.total_taxable_amount or 0.0, 2),
            "total_tax": round(row.total_tax or 0.0, 2),
            "total_revenue": round(row.total_revenue or 0.0, 2),
        }
        for row in results
    ]

    return {
        "page": page,
        "limit": limit,
        "total_records": total_count,
        "total_pages": (total_count + limit - 1) // limit,
        "data": items
    }


# ---------------------------------------------------------------------------
# 2. GET /inventory - Dynamically calculated Stock Levels (Current, Reserved, Available)
# ---------------------------------------------------------------------------
@router.get("/inventory")
def get_inventory_report(
    warehouse_id: Optional[int] = Query(None, description="Filter by Warehouse ID"),
    hub_id: Optional[int] = Query(None, description="Filter by Hub ID"),
    search: Optional[str] = Query(None, description="Search by SKU, Product Name, Category, Brand"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns inventory stock levels joining Inventory, Product, and Warehouse tables.
    Dynamically verifies Available Stock = Current Stock - Reserved Stock.
    """
    query = db.query(
        Inventory.id.label("inventory_id"),
        Product.id.label("product_id"),
        Product.sku,
        Product.name.label("product_name"),
        Product.category,
        Product.brand,
        Warehouse.id.label("warehouse_id"),
        Warehouse.name.label("warehouse_name"),
        Warehouse.warehouse_type.label("warehouse_type"),
        StateHub.id.label("hub_id"),
        StateHub.hub_name.label("hub_name"),
        Inventory.current_qty,
        Inventory.reserved_qty,
        Inventory.available_qty,
        Inventory.last_updated
    ).join(Product, Product.id == Inventory.product_id)\
     .join(Warehouse, Warehouse.id == Inventory.warehouse_id)\
     .outerjoin(StateHub, StateHub.id == Warehouse.hub_id)\
     .filter(Inventory.company_id == company_id)

    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    if hub_id:
        query = query.filter(Warehouse.hub_id == hub_id)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.sku.ilike(search_pattern),
                Product.name.ilike(search_pattern),
                Product.category.ilike(search_pattern),
                Product.brand.ilike(search_pattern),
                Warehouse.name.ilike(search_pattern)
            )
        )

    total_records = query.count()
    skip = (page - 1) * limit
    results = query.order_by(Product.sku.asc()).offset(skip).limit(limit).all()

    items = [
        {
            "inventory_id": r.inventory_id,
            "product_id": r.product_id,
            "sku": r.sku,
            "product_name": r.product_name,
            "category": r.category,
            "brand": r.brand,
            "warehouse_id": r.warehouse_id,
            "warehouse_name": r.warehouse_name,
            "warehouse_type": r.warehouse_type.value if r.warehouse_type else None,
            "hub_id": r.hub_id,
            "hub_name": r.hub_name,
            "current_qty": r.current_qty,
            "reserved_qty": r.reserved_qty,
            "available_qty": r.current_qty - r.reserved_qty,  # Dynamic calculation
            "last_updated": r.last_updated.isoformat() if r.last_updated else None
        }
        for r in results
    ]

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": items
    }


# ---------------------------------------------------------------------------
# 3. GET /dispatches - Paginated FCDispatch Reports
# ---------------------------------------------------------------------------
@router.get("/dispatches")
def get_fc_dispatches_report(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    warehouse_id: Optional[int] = Query(None, description="Filter by Warehouse ID"),
    status: Optional[str] = Query(None, description="Dispatch status filter"),
    search: Optional[str] = Query(None, description="Search by dispatch number"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns paginated FC Dispatch records with associated warehouse and document numbers.
    """
    query = db.query(FCDispatch).filter(FCDispatch.company_id == company_id)

    if warehouse_id:
        query = query.filter(FCDispatch.warehouse_id == warehouse_id)
    if status:
        query = query.filter(FCDispatch.dispatch_status == status)
    if date_from:
        query = query.filter(FCDispatch.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(FCDispatch.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        query = query.filter(FCDispatch.dispatch_number.ilike(f"%{search}%"))

    total_records = query.count()
    skip = (page - 1) * limit
    dispatches = query.order_by(FCDispatch.created_at.desc()).offset(skip).limit(limit).all()

    data = []
    for d in dispatches:
        total_items = sum(item.quantity for item in d.items) if d.items else 0
        total_value = sum(item.total_amount for item in d.items) if d.items else 0.0

        data.append({
            "id": d.id,
            "dispatch_number": d.dispatch_number,
            "dispatch_status": d.dispatch_status,
            "warehouse_id": d.warehouse_id,
            "warehouse_name": d.warehouse.name if d.warehouse else None,
            "invoice_number": d.invoice.invoice_number if d.invoice else None,
            "challan_number": d.delivery_challan.challan_number if d.delivery_challan else None,
            "total_items": total_items,
            "total_value": round(total_value, 2),
            "created_at": d.created_at.isoformat() if d.created_at else None
        })

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": data
    }


# ---------------------------------------------------------------------------
# 4. GET /returns - Paginated FCReturn Reports
# ---------------------------------------------------------------------------
@router.get("/returns")
def get_fc_returns_report(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    warehouse_id: Optional[int] = Query(None, description="Filter by Warehouse ID"),
    status: Optional[str] = Query(None, description="Return status filter"),
    search: Optional[str] = Query(None, description="Search by return number"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns paginated Fulfillment Center Returns records.
    """
    query = db.query(FCReturn).filter(FCReturn.company_id == company_id)

    if warehouse_id:
        query = query.filter(FCReturn.warehouse_id == warehouse_id)
    if status:
        query = query.filter(FCReturn.status == status)
    if date_from:
        query = query.filter(FCReturn.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(FCReturn.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        query = query.filter(FCReturn.return_number.ilike(f"%{search}%"))

    total_records = query.count()
    skip = (page - 1) * limit
    returns = query.order_by(FCReturn.created_at.desc()).offset(skip).limit(limit).all()

    data = []
    for r in returns:
        total_returned_qty = sum(item.quantity for item in r.items) if r.items else 0
        data.append({
            "id": r.id,
            "return_number": r.return_number,
            "status": r.status,
            "warehouse_id": r.warehouse_id,
            "warehouse_name": r.warehouse.name if r.warehouse else None,
            "dispatch_id": r.dispatch_id,
            "dispatch_number": r.dispatch.dispatch_number if r.dispatch else None,
            "total_returned_qty": total_returned_qty,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": data
    }


# ---------------------------------------------------------------------------
# 5. GET /defective - Paginated Damage Claims & Defective Inventory Reports
# ---------------------------------------------------------------------------
@router.get("/defective")
def get_defective_reports(
    report_type: str = Query("claims", pattern="^(claims|inventory)$", description="claims or inventory"),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    warehouse_id: Optional[int] = Query(None, description="Filter by Warehouse ID"),
    status: Optional[str] = Query(None, description="Status filter"),
    search: Optional[str] = Query(None, description="Search by SKU, claim number, or return ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns paginated Damage Claims and Defective Inventory records.
    """
    skip = (page - 1) * limit

    if report_type == "claims":
        query = db.query(DamageClaim).filter(DamageClaim.company_id == company_id)

        if warehouse_id:
            query = query.filter(DamageClaim.warehouse_id == warehouse_id)
        if status:
            query = query.filter(DamageClaim.claim_status == status)
        if date_from:
            query = query.filter(DamageClaim.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(DamageClaim.created_at <= datetime.combine(date_to, datetime.max.time()))
        if search:
            search_pattern = f"%{search}%"
            query = query.join(Product, Product.id == DamageClaim.product_id)\
                         .filter(or_(DamageClaim.claim_number.ilike(search_pattern), Product.sku.ilike(search_pattern)))

        total_records = query.count()
        claims = query.order_by(DamageClaim.created_at.desc()).offset(skip).limit(limit).all()

        data = [
            {
                "id": c.id,
                "claim_number": c.claim_number,
                "warehouse_id": c.warehouse_id,
                "warehouse_name": c.warehouse.name if c.warehouse else None,
                "product_id": c.product_id,
                "sku": c.product.sku if c.product else None,
                "product_name": c.product.name if c.product else None,
                "quantity": c.quantity,
                "claim_status": c.claim_status,
                "video_reference": c.video_reference,
                "remarks": c.remarks,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in claims
        ]
    else:
        query = db.query(DefectiveInventory).filter(DefectiveInventory.company_id == company_id)

        if status:
            query = query.filter(DefectiveInventory.status == status)
        if date_from:
            query = query.filter(DefectiveInventory.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(DefectiveInventory.created_at <= datetime.combine(date_to, datetime.max.time()))
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    DefectiveInventory.sku_snapshot.ilike(search_pattern),
                    DefectiveInventory.product_name_snapshot.ilike(search_pattern)
                )
            )

        total_records = query.count()
        items = query.order_by(DefectiveInventory.created_at.desc()).offset(skip).limit(limit).all()

        data = [
            {
                "id": i.id,
                "amazon_return_id": i.amazon_return_id,
                "product_id": i.product_id,
                "sku": i.sku_snapshot,
                "product_name": i.product_name_snapshot,
                "quantity": i.quantity,
                "return_reason": i.return_reason,
                "inspection_notes": i.inspection_notes,
                "status": i.status,
                "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
                "created_at": i.created_at.isoformat() if i.created_at else None
            }
            for i in items
        ]

    return {
        "report_type": report_type,
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": data
    }

import io
import csv
from fastapi.responses import Response

# ---------------------------------------------------------------------------
# EXPORT ENDPOINTS
# ---------------------------------------------------------------------------
@router.get("/sales/export")
def export_sales(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    if group_by == "month":
        period_col = func.strftime("%Y-%m", Sale.sale_date).label("period")
    elif group_by == "week":
        period_col = func.strftime("%Y-%W", Sale.sale_date).label("period")
    else:
        period_col = func.date(Sale.sale_date).label("period")

    # 1. Filter Sales First (No Joins)
    sale_base = db.query(
        Sale.id,
        period_col,
        Sale.total_taxable_amount,
        Sale.total_tax,
        Sale.grand_total
    ).filter(Sale.company_id == company_id)

    if date_from:
        sale_base = sale_base.filter(Sale.sale_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        sale_base = sale_base.filter(Sale.sale_date <= datetime.combine(date_to, datetime.max.time()))
    if status:
        sale_base = sale_base.filter(Sale.status == status)
    if search:
        search_pattern = f"%{search}%"
        sale_base = sale_base.filter(
            or_(Sale.bill_number.ilike(search_pattern), Sale.invoice_number.ilike(search_pattern), Sale.customer_name.ilike(search_pattern))
        )

    sale_sq = sale_base.subquery()

    item_sq = db.query(
        SaleItem.sale_id,
        func.sum(SaleItem.quantity).label("qty")
    ).group_by(SaleItem.sale_id).subquery()

    query = db.query(
        sale_sq.c.period,
        func.count(sale_sq.c.id).label("total_orders"),
        func.sum(func.coalesce(item_sq.c.qty, 0)).label("total_items_sold"),
        func.sum(sale_sq.c.total_taxable_amount).label("total_taxable_amount"),
        func.sum(sale_sq.c.total_tax).label("total_tax"),
        func.sum(sale_sq.c.grand_total).label("total_revenue")
    ).outerjoin(item_sq, item_sq.c.sale_id == sale_sq.c.id)

    query = query.group_by(sale_sq.c.period).order_by(sale_sq.c.period.desc())
    results = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Period", "Total Orders", "Total Items Sold", "Total Taxable Amount", "Total Tax", "Total Revenue"])
    for row in results:
        writer.writerow([row.period, row.total_orders, row.total_items_sold, round(row.total_taxable_amount or 0, 2), round(row.total_tax or 0, 2), round(row.total_revenue or 0, 2)])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sales_report.csv"})

@router.get("/sales/detailed/export")
def export_detailed_sales(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    query = db.query(
        Sale.bill_number,
        Sale.customer_name,
        Sale.sale_date,
        SaleItem.sku,
        Product.name.label("product_name"),
        SaleItem.quantity,
        SaleItem.selling_price,
        SaleItem.line_total
    ).join(
        SaleItem, Sale.id == SaleItem.sale_id
    ).join(
        Product, SaleItem.product_id == Product.id
    ).filter(Sale.company_id == company_id)

    if date_from:
        query = query.filter(Sale.sale_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Sale.sale_date <= datetime.combine(date_to, datetime.max.time()))
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Sale.bill_number.ilike(search_pattern),
                Sale.customer_name.ilike(search_pattern),
                SaleItem.sku.ilike(search_pattern),
                Product.name.ilike(search_pattern)
            )
        )

    query = query.order_by(Sale.sale_date.desc(), Sale.bill_number)
    results = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Bill Number", "Customer Name", "Sale Date", "SKU", "Product Name", "Quantity", "Unit Price", "Line Total"])
    for row in results:
        writer.writerow([
            row.bill_number,
            row.customer_name or "",
            row.sale_date.isoformat() if row.sale_date else "",
            row.sku,
            row.product_name,
            row.quantity,
            round(row.selling_price or 0, 2),
            round(row.line_total or 0, 2)
        ])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=detailed_sales_report.csv"})

@router.get("/inventory/export")
def export_inventory(
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    query = db.query(Inventory, Product, Warehouse).join(Product, Inventory.product_id == Product.id).join(Warehouse, Inventory.warehouse_id == Warehouse.id).filter(Inventory.company_id == company_id)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern), Warehouse.name.ilike(search_pattern))
        )
    results = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product SKU", "Product Name", "Warehouse", "Available Qty", "Current Qty", "Reserved Qty"])
    for inv, prod, wh in results:
        writer.writerow([prod.sku, prod.name, wh.name, inv.available_qty, inv.current_qty, inv.reserved_qty])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inventory_report.csv"})

@router.get("/dispatches/export")
def export_dispatches(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    query = db.query(FCDispatch).filter(FCDispatch.company_id == company_id)
    if status:
        query = query.filter(FCDispatch.dispatch_status == status)
    if date_from:
        query = query.filter(FCDispatch.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(FCDispatch.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        query = query.filter(FCDispatch.dispatch_number.ilike(f"%{search}%"))
        
    results = query.order_by(FCDispatch.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Dispatch Number", "Status", "Date"])
    for d in results:
        writer.writerow([d.dispatch_number, d.dispatch_status, d.created_at.isoformat() if d.created_at else ""])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dispatch_report.csv"})

@router.get("/returns/export")
def export_returns(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    query = db.query(FCReturn).filter(FCReturn.company_id == company_id)
    if status:
        query = query.filter(FCReturn.status == status)
    if date_from:
        query = query.filter(FCReturn.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(FCReturn.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        query = query.filter(FCReturn.return_number.ilike(f"%{search}%"))
        
    results = query.order_by(FCReturn.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Return Number", "Status", "Date"])
    for r in results:
        writer.writerow([r.return_number, r.status, r.created_at.isoformat() if r.created_at else ""])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=returns_report.csv"})

@router.get("/defective/export")
def export_defective(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    query = db.query(DefectiveInventory).filter(DefectiveInventory.company_id == company_id)
    if status:
        query = query.filter(DefectiveInventory.status == status)
    if date_from:
        query = query.filter(DefectiveInventory.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(DefectiveInventory.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(DefectiveInventory.sku_snapshot.ilike(search_pattern), DefectiveInventory.product_name_snapshot.ilike(search_pattern)))
        
    results = query.order_by(DefectiveInventory.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["SKU", "Product Name", "Quantity", "Reason", "Status", "Inspection Date", "Created At"])
    for d in results:
        writer.writerow([d.sku_snapshot, d.product_name_snapshot, d.quantity, d.return_reason, d.status, d.inspection_date.isoformat() if d.inspection_date else "", d.created_at.isoformat() if d.created_at else ""])
    
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=defective_report.csv"})
