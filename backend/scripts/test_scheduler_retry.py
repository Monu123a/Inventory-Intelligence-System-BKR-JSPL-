import os
import sys
import time
from pathlib import Path
from sqlalchemy.orm import Session
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.db import SessionLocal
from app.models.schema import Company, User, JobExecutionLog
from app.services.scheduler_service import execute_job_with_logging

class MockSchedulerJob:
    def __init__(self):
        self.call_count = 0
        
    def execute(self, db, company_id):
        self.call_count += 1
        if self.call_count == 1:
            raise Exception("Network Timeout on first attempt")
        return {"status": "success", "records": 5}

def test_scheduler_retry():
    db = SessionLocal()
    try:
        company = Company(name="Scheduler Co", code="SCHED")
        db.add(company)
        db.commit()
        
        job = MockSchedulerJob()
        
        print("Run 1: Triggering scheduler job (will fail)")
        try:
            execute_job_with_logging("MockJob", job.execute, company.id)
            print("❌ FAILURE: Job did not throw exception as expected")
        except Exception as e:
            print(f"✅ Caught expected job exception: {e}")
            
        print("Run 2: Triggering scheduler job (will succeed - simulating manual or next cron tick)")
        execute_job_with_logging("MockJob", job.execute, company.id)
        
        print("Verifying JobExecutionLog entries...")
        logs = db.query(JobExecutionLog).filter(JobExecutionLog.company_id == company.id).order_by(JobExecutionLog.start_time).all()
        
        assert len(logs) == 2, f"Expected 2 log entries, found {len(logs)}"
        
        # Verify first log
        assert logs[0].status == "Failed", "First log should be Failed"
        assert "Network Timeout" in logs[0].error_message, "First log should contain error message"
        
        # Verify second log
        assert logs[1].status == "Success", "Second log should be Success"
        assert logs[1].error_message is None, "Second log should not have an error message"
        
        # NOTE: APScheduler (as configured in scheduler_service.py) does not automatically retry exceptions.
        # So "retry behavior (if intended)" is NOT intended by the current architecture. The system relies 
        # on the next cron interval or manual triggering for a retry, logging each distinct attempt cleanly.
        print("✅ SCHEDULER FAILURE VERIFIED: Proper logging observed, no automatic duplicate execution/retry within the wrapper.")
        
    finally:
        # Cleanup
        try:
            db.query(JobExecutionLog).filter(JobExecutionLog.company_id == company.id).delete()
            db.query(Company).filter(Company.id == company.id).delete()
            db.commit()
        except:
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    test_scheduler_retry()
