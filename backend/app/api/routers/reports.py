from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from typing import Optional

from app.models.db import get_db

from app.models.schema import ReportHistory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

router = APIRouter(prefix="/reports", tags=["Reports"])

from app.services.report_service import ReportService
from app.api.dependencies import get_current_company_id, require_manager
from app.core.limiter import limiter
from app.services.metrics_service import log_metric
import time

@router.post("/generate/low-stock")
@limiter.limit("3/minute")
def generate_low_stock_report(request: Request, format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), manager_user = Depends(require_manager)):
    try:
        start_t = time.time()
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_low_stock(db, company_id=company_id, format=ext)
        db.commit()
        log_metric("report_generation_time_ms", (time.time() - start_t)*1000, {"type": "low_stock"})
        return {"data": {"message": "Report generated", "download_link": report.download_link}}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/negative-stock")
@limiter.limit("3/minute")
def generate_negative_stock_report(request: Request, format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), manager_user = Depends(require_manager)):
    try:
        start_t = time.time()
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_negative_stock(db, company_id=company_id, format=ext)
        db.commit()
        log_metric("report_generation_time_ms", (time.time() - start_t)*1000, {"type": "negative_stock"})
        return {"data": {"message": "Report generated", "download_link": report.download_link}}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/daily-replenishment")
@limiter.limit("3/minute")
def generate_daily_replenishment_report(request: Request, format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), manager_user = Depends(require_manager)):
    try:
        start_t = time.time()
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_replenishment(db, company_id=company_id, format=ext)
        db.commit()
        log_metric("report_generation_time_ms", (time.time() - start_t)*1000, {"type": "daily_replenishment"})
        return {"data": {"message": "Report generated", "download_link": report.download_link}}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/history")
def get_report_history(
    report_type: Optional[str] = None, 
    skip: int = 0,
    limit: int = 100,
    company_id: int = Depends(get_current_company_id), 
    db: Session = Depends(get_db),
    manager_user = Depends(require_manager)
):
    query = db.query(ReportHistory).filter(ReportHistory.company_id == company_id)
    if report_type:
        query = query.filter(ReportHistory.report_type == report_type)
        
    total = query.count()
    items = query.order_by(ReportHistory.generated_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "data": items,
        "total": total,
        "meta": {"skip": skip, "limit": limit}
    }

@router.get("/download/{filename}")
def download_report(filename: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db), manager_user = Depends(require_manager)):
    safe_filename = os.path.basename(filename)

    matched_report = db.query(ReportHistory).filter(
        ReportHistory.company_id == company_id,
        ReportHistory.file_path.endswith(safe_filename)
    ).first()

    if not matched_report:
        raise HTTPException(status_code=404, detail="File not found")

    filepath = matched_report.file_path
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=safe_filename)

from app.services.series_report_service import SeriesReportService
from fastapi import Response
from datetime import date

@router.get("/series-wise/list")
def get_series_list(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """Returns detected invoice and order series available for filtering."""
    series = SeriesReportService.get_detected_series(db, company_id=company_id)
    return {"data": series}

@router.get("/series-wise/export")
def export_series_wise_sales_report(
    report_type: str = Query("sales", description="Category: sales, purchases, inventory, amazon_returns, sales_returns, amazon_mtr"),
    series: str = Query("GST", description="Series name: GST, AMAZON, BKR, JGST, ALL, or custom prefix"),
    vendor_id: Optional[int] = Query(None, description="Optional Vendor ID for purchase reports"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    format: str = Query("csv", pattern="^(csv|excel)$"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """
    Generates and downloads the exact 47-column Accountant Report (Sales, Purchases, Amazon Returns, Sales Returns).
    """
    try:
        content, filename, media_type, row_count = SeriesReportService.generate_accountant_report(
            db=db,
            report_type=report_type,
            company_id=company_id,
            series=series,
            vendor_id=vendor_id,
            date_from=date_from,
            date_to=date_to,
            file_format=format
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Row-Count": str(row_count)
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/purchases/export")
def export_purchases_report(
    vendor_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|excel)$"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """Generates the official 47-column Purchase Register."""
    try:
        content, filename, media_type, row_count = SeriesReportService.generate_purchase_report(
            db=db, company_id=company_id, vendor_id=vendor_id,
            date_from=date_from, date_to=date_to, file_format=format
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Row-Count": str(row_count)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate purchase report: {str(e)}")

@router.get("/returns/export")
def export_returns_report(
    return_source: str = Query("amazon", pattern="^(amazon|pos|sales)$"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|excel)$"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """Generates the official 47-column Returns Register."""
    from app.utils.date_utils import parse_date_param
    parsed_date_from = parse_date_param(date_from)
    parsed_date_to = parse_date_param(date_to)
    try:
        if return_source == "amazon":
            content, filename, media_type, row_count = SeriesReportService.generate_amazon_returns_report(
                db=db, company_id=company_id, date_from=parsed_date_from, date_to=parsed_date_to, file_format=format
            )
        else:
            content, filename, media_type, row_count = SeriesReportService.generate_sales_returns_report(
                db=db, company_id=company_id, date_from=parsed_date_from, date_to=parsed_date_to, file_format=format
            )
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Row-Count": str(row_count)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate returns report: {str(e)}")


@router.get("/amazon-mtr/warehouses")
def get_amazon_mtr_warehouses(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """Returns warehouses and FCs available for filtering the Amazon MTR report."""
    from app.models.schema import Warehouse, StateHub, AmazonLiveAllocation
    whs = db.query(Warehouse).filter(
        Warehouse.company_id == company_id,
        Warehouse.status == "ACTIVE"
    ).order_by(Warehouse.id.asc()).all()

    # Pre-count allocations per warehouse
    counts = dict(
        db.query(AmazonLiveAllocation.warehouse_id, func.count(AmazonLiveAllocation.id))
        .filter(AmazonLiveAllocation.company_id == company_id)
        .group_by(AmazonLiveAllocation.warehouse_id)
        .all()
    )

    hub_map = {h.id: h for h in db.query(StateHub).all()}

    results = []
    total_allocs = sum(counts.values())
    results.append({
        "code": "ALL",
        "name": "All Warehouses & FCs",
        "state": "All India",
        "gstin": "",
        "order_count": total_allocs
    })

    for w in whs:
        code = (w.code or "").strip().upper()
        if not code or code in ("DEFAULT", "TEST-WH-MFN", "AUTO_GODOWN"):
            continue
        hub = hub_map.get(w.hub_id) if w.hub_id else None
        results.append({
            "code": code,
            "name": w.name,
            "state": hub.state if hub else "",
            "gstin": hub.gstin if hub else "",
            "order_count": counts.get(w.id, 0)
        })

    return {"data": results}


@router.get("/amazon-mtr/export")
def export_amazon_mtr_report(
    warehouse_code: Optional[str] = Query(None, description="Warehouse or FC code: VSHB, IN, KWZ2, BLR4, BOM5, etc. or ALL"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    format: str = Query("excel", pattern="^(excel|csv)$"),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    """
    Exports the official 86-column Amazon Merchant Tax Report (MTR / Logic ERP format)
    matching the accountant format, filterable by warehouse / FC code.
    """
    try:
        content, filename, media_type, row_count = SeriesReportService.generate_amazon_mtr_report(
            db=db,
            company_id=company_id,
            warehouse_code=warehouse_code,
            date_from=date_from,
            date_to=date_to,
            file_format=format
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Row-Count": str(row_count)
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate Amazon MTR report: {str(e)}")



