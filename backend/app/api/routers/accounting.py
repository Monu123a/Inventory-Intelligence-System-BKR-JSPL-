from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
import os
import zipfile
import io

from app.api.dependencies import get_db, get_current_user, get_current_company_id
from app.models.schema import Sale, User
from app.models.accounting_schema import AccountingExportBatch, AccountingExportLog, AccountingMapping, AccountingConfiguration
from app.services.accounting.integration_engine import AccountingIntegrationEngine
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/accounting", tags=["Accounting Integration"])

# --- Models ---
class ExportBatchRequest(BaseModel):
    sale_ids: List[int]

class MappingCreate(BaseModel):
    mapping_type: str
    erp_reference: str
    accounting_name: str

class ConfigurationUpdate(BaseModel):
    default_sales_ledger: str
    default_godown: str
    round_off_ledger: str

# --- Endpoints ---

@router.get("/invoices")
def get_ready_invoices(profile: str = "all", company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    """
    Returns all sales along with their export lifecycle status.
    Supports profile: 'today', 'yesterday', 'pending', 'failed', 'all'
    """
    query = db.query(Sale).filter(Sale.company_id == company_id)
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if profile == "today":
        query = query.filter(Sale.sale_date >= today)
    elif profile == "yesterday":
        query = query.filter(Sale.sale_date >= today - timedelta(days=1), Sale.sale_date < today)
        
    sales = query.order_by(desc(Sale.sale_date)).limit(200).all()
    
    # Get latest export log for each sale
    logs = db.query(AccountingExportLog).filter(AccountingExportLog.company_id == company_id).all()
    log_map = {log.sale_id: log for log in logs}
    
    results = []
    for sale in sales:
        log = log_map.get(sale.id)
        results.append({
            "id": sale.id,
            "invoice_number": sale.invoice_number or sale.bill_number,
            "invoice_date": sale.sale_date,
            "customer_name": sale.customer_name,
            "invoice_type": sale.invoice_type,
            "grand_total": sale.grand_total,
            "export_status": log.status if log else "Ready",
            "last_error": log.last_error if log else None,
            "retry_count": log.retry_count if log else 0,
            "last_export_time": log.last_export_time if log else None
        })
        
    if profile == "pending":
        results = [r for r in results if r["export_status"] in ["Ready", "Queued"]]
    elif profile == "failed":
        results = [r for r in results if r["export_status"] == "Failed"]
        
    return results

@router.post("/export/batch")
def export_batch(request: ExportBatchRequest, company_id: int = Depends(get_current_company_id), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generates a batch XML for the requested invoices.
    """
    engine = AccountingIntegrationEngine(db, company_id)
    batch = engine.export_invoices(request.sale_ids, user_id=user.id)
    
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "invoice_count": batch.invoice_count,
        "errors": batch.errors
    }

@router.get("/export/history")
def get_export_history(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    batches = db.query(AccountingExportBatch).filter(AccountingExportBatch.company_id == company_id).order_by(desc(AccountingExportBatch.generated_at)).limit(50).all()
    results = []
    for b in batches:
        results.append({
            "id": b.id,
            "batch_type": b.batch_type,
            "generated_at": b.generated_at,
            "generated_by": b.creator.username if b.creator else "System",
            "status": b.status,
            "invoice_count": b.invoice_count,
            "errors": b.errors,
            "has_file": bool(b.file_path)
        })
    return results

@router.get("/export/download/{batch_id}")
def download_batch_xml(batch_id: int, format: str = "xml", company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    batch = db.query(AccountingExportBatch).filter(AccountingExportBatch.id == batch_id, AccountingExportBatch.company_id == company_id).first()
    if not batch or not batch.file_path:
        raise HTTPException(status_code=404, detail="Batch XML file not found.")
        
    if format == "zip":
        # Create a ZIP containing the XML and the Manifest JSON
        import io
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # Add XML
            if not os.path.exists(batch.file_path):
                raise HTTPException(status_code=404, detail="Batch file is missing from disk.")
            zip_file.write(batch.file_path, arcname=os.path.basename(batch.file_path))
            # Add Manifest
            manifest_path = batch.file_path.replace('.xml', '_manifest.json')
            if os.path.exists(manifest_path):
                zip_file.write(manifest_path, arcname=os.path.basename(manifest_path))
                
        # Send ZIP response
        from fastapi.responses import StreamingResponse
        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]), 
            media_type="application/x-zip-compressed", 
            headers={"Content-Disposition": f"attachment; filename=Batch_{batch_id}_Export.zip"}
        )
    else:
        return FileResponse(path=batch.file_path, filename=f"Tally_Export_Batch_{batch_id}.xml", media_type='application/xml')

@router.get("/statistics")
def get_statistics(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Simple KPIs
    pending = db.query(Sale).filter(Sale.company_id == company_id).count() - db.query(AccountingExportLog).filter(AccountingExportLog.company_id == company_id, AccountingExportLog.status.in_(["Generated", "Downloaded", "Imported"])).count()
    generated_today = db.query(AccountingExportBatch).filter(AccountingExportBatch.company_id == company_id, AccountingExportBatch.generated_at >= today).count()
    failed = db.query(AccountingExportLog).filter(AccountingExportLog.company_id == company_id, AccountingExportLog.status == "Failed").count()
    
    # Optional: We could do sum of Grand Total of all today's batches.
    
    return {
        "pending_exports": max(0, pending),
        "generated_today": generated_today,
        "failed_exports": failed,
        "total_value": 0 # stubbed
    }

@router.get("/mapping")
def get_mappings(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    mappings = db.query(AccountingMapping).filter(AccountingMapping.company_id == company_id).all()
    return mappings

@router.post("/mapping")
def create_mapping(req: MappingCreate, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    mapping = db.query(AccountingMapping).filter_by(company_id=company_id, mapping_type=req.mapping_type, erp_reference=req.erp_reference).first()
    if mapping:
        mapping.accounting_name = req.accounting_name
    else:
        mapping = AccountingMapping(
            company_id=company_id,
            mapping_type=req.mapping_type,
            erp_reference=req.erp_reference,
            accounting_name=req.accounting_name
        )
        db.add(mapping)
    db.commit()
    return {"status": "success"}

@router.get("/configuration")
def get_configuration(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    config = db.query(AccountingConfiguration).filter_by(company_id=company_id).first()
    if not config:
        config = AccountingConfiguration(company_id=company_id)
        db.add(config)
        db.commit()
    return config

@router.post("/configuration")
def update_configuration(req: ConfigurationUpdate, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    config = db.query(AccountingConfiguration).filter_by(company_id=company_id).first()
    if not config:
        config = AccountingConfiguration(company_id=company_id)
        db.add(config)
        
    config.default_sales_ledger = req.default_sales_ledger
    config.default_godown = req.default_godown
    config.round_off_ledger = req.round_off_ledger
    db.commit()
    return config
