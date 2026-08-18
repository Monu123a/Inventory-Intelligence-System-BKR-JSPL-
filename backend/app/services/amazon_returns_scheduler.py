import logging
import time
from datetime import datetime

from app.models.db import SessionLocal
from app.models.schema import Company, CompanySettings, AmazonReturnSyncLog
from app.services.amazon_returns_service import AmazonReturnsService
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

def run_amazon_returns_sync_job(company_id: int):
    """
    Executes the Amazon Returns Sync for a specific company, logs the execution,
    and handles failures gracefully.
    """
    db = SessionLocal()
    start_time = datetime.utcnow()
    start_time_ts = time.time()
    
    # Create the running log
    log_entry = AmazonReturnSyncLog(
        company_id=company_id,
        started_at=start_time,
        status="Running"
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    status = "Failed"
    error_msg = None
    records_created = 0
    records_updated = 0
    
    try:
        # Perform the actual sync
        records_created, records_updated = AmazonReturnsService.sync_returns(db, company_id=company_id)
        status = "Success"
    except Exception as e:
        logger.error(f"Amazon Returns Sync failed for company {company_id}: {e}", exc_info=True)
        error_msg = str(e)
        raise
    finally:
        end_time_ts = time.time()
        
        # Update the log
        log_entry.completed_at = datetime.utcnow()
        log_entry.duration = end_time_ts - start_time_ts
        log_entry.status = status
        log_entry.error_message = error_msg
        log_entry.records_created = records_created
        log_entry.records_updated = records_updated
        
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update AmazonReturnSyncLog for company {company_id}: {e}", exc_info=True)
            raise
        db.close()

def _orchestrate_amazon_returns_sync():
    """
    Orchestrator: fetches all active companies that have amazon returns sync enabled,
    and runs the sync job for each one.
    """
    db = SessionLocal()
    try:
        # Find companies where amazon_returns_sync_enabled is True
        settings = db.query(CompanySettings).filter(CompanySettings.amazon_returns_sync_enabled == True).all()
        for setting in settings:
            # Check if company is Active
            company = db.query(Company).filter(Company.id == setting.company_id, Company.status == "Active").first()
            if company:
                logger.info(f"Triggering Amazon Returns Sync for company {company.code} (ID: {company.id})")
                run_amazon_returns_sync_job(company_id=company.id)
    finally:
        db.close()

def register_amazon_returns_jobs(scheduler):
    """
    Registers the Amazon Returns Sync orchestrator in the main APScheduler instance.
    For simplicity, it polls every 5 minutes and checks which companies are enabled.
    """
    scheduler.add_job(
        _orchestrate_amazon_returns_sync,
        IntervalTrigger(minutes=5),
        id="amazon_returns_sync",
        replace_existing=True
    )
    logger.info("Registered Amazon Returns Sync job (Interval: 5m)")
