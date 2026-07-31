from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import pandas as pd
import os
from typing import List, Optional

from app.models.db import get_db

from app.models.schema import Inventory, Product, Warehouse, InventoryMovement, ReportHistory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

router = APIRouter(prefix="/reports", tags=["Reports"])

from app.services.report_service import ReportService, REPORTS_DIR
from app.api.dependencies import get_current_company_id

@router.post("/generate/low-stock")
def generate_low_stock_report(format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_low_stock(db, company_id=company_id, format=ext)
        return {"message": "Report generated", "download_link": report.download_link}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/negative-stock")
def generate_negative_stock_report(format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_negative_stock(db, company_id=company_id, format=ext)
        return {"message": "Report generated", "download_link": report.download_link}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/daily-replenishment")
def generate_daily_replenishment_report(format: str = Query("excel", pattern="^(excel|csv)$"), company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        ext = "csv" if format == "csv" else "xlsx"
        report = ReportService.generate_replenishment(db, company_id=company_id, format=ext)
        return {"message": "Report generated", "download_link": report.download_link}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/history")
def get_report_history(report_type: Optional[str] = None, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    query = db.query(ReportHistory).filter(ReportHistory.company_id == company_id).order_by(ReportHistory.generated_at.desc())
    if report_type:
        query = query.filter(ReportHistory.report_type == report_type)
    return query.all()

@router.get("/download/{filename}")
def download_report(filename: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    safe_filename = os.path.basename(filename)

    report = db.query(ReportHistory).filter(
        ReportHistory.company_id == company_id
    ).order_by(ReportHistory.generated_at.desc()).all()

    matched_report = next(
        (item for item in report if os.path.basename(item.file_path) == safe_filename),
        None
    )
    if not matched_report:
        raise HTTPException(status_code=404, detail="File not found")

    filepath = matched_report.file_path
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=safe_filename)
