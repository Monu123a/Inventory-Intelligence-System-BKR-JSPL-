import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.db import SessionLocal
from app.models.schema import Company, User, Warehouse, Product, AmazonReturn
from app.services.amazon_returns_service import AmazonReturnsService
import app.services.amazon_returns_service as ars

def setup_test_data(db: Session):
    company = Company(name="Amazon Batch Co", code="AMZBT")
    db.add(company)
    db.flush()
    
    wh1 = Warehouse(name="WH1", code="AMZ-BWH", company_id=company.id)
    db.add(wh1)
    db.flush()
    
    # We will create 2 valid products, 1 will be missing from DB (should auto-create), 
    # and 1 will have invalid data
    prod1 = Product(name="Item 1", sku="AMZ-101", company_id=company.id)
    prod2 = Product(name="Item 2", sku="AMZ-102", company_id=company.id)
    db.add_all([prod1, prod2])
    db.commit()
    
    return company, wh1, prod1, prod2

class MockAmazonBatchClient:
    def fetch_returns(self, since=None):
        return [
            # Valid Record 1
            {
                "amazon_return_id": "RET-001",
                "order_item_id": "IT-1",
                "amazon_order_id": "ORD-1",
                "sku": "AMZ-101",
                "return_reason": "DEFECTIVE",
                "return_status": "RETURNED",
                "quantity": 1
            },
            # Valid Record 2
            {
                "amazon_return_id": "RET-002",
                "order_item_id": "IT-2",
                "amazon_order_id": "ORD-2",
                "sku": "AMZ-102",
                "return_reason": "DEFECTIVE",
                "return_status": "RETURNED",
                "quantity": 1
            },
            # Invalid Record (Will cause IntegrityError or ValueError because amazon_return_id is None)
            {
                "amazon_return_id": None, # Will violate NOT NULL
                "order_item_id": "IT-3",
                "amazon_order_id": "ORD-3",
                "sku": "AMZ-103",
                "return_reason": "DEFECTIVE",
                "return_status": "RETURNED",
                "quantity": 1
            },
            # Valid Record 4
            {
                "amazon_return_id": "RET-004",
                "order_item_id": "IT-4",
                "amazon_order_id": "ORD-4",
                "sku": "AMZ-104",
                "return_reason": "DEFECTIVE",
                "return_status": "RETURNED",
                "quantity": 1
            }
        ]

def test_amazon_batch_failure():
    db = SessionLocal()
    try:
        print("Setting up amazon batch test data...")
        company, wh1, p1, p2 = setup_test_data(db)
        
        with patch.object(ars, 'get_amazon_returns_client', return_value=MockAmazonBatchClient()):
            print("Run 1: Syncing batch with 1 invalid record...")
            
            try:
                created, updated = AmazonReturnsService.sync_returns(db, company.id)
                print(f"Run 1 Results - Created: {created}, Updated: {updated}")
                # Wait, sync_returns explicitly RAISES Exception("PartialBatchFailureException") if failed_records exist.
                # So it should throw.
                print("❌ FAILURE: Batch did not throw PartialBatchFailureException!")
            except Exception as e:
                print(f"✅ Caught expected batch exception: {e}")
                
            # Verify that EXACTLY 3 records persisted (the valid ones) despite the 1 failure in the loop.
            # This proves the loop caught the error, rolled back the INDIVIDUAL record, and continued.
            count = db.query(AmazonReturn).filter(AmazonReturn.company_id == company.id).count()
            
            print(f"Total successful records persisted: {count}")
            assert count == 3, f"Expected 3 successful records, found {count}. (Silent data loss or batch abort)"
            
            # Verify the specific successful ones exist
            ret1 = db.query(AmazonReturn).filter(AmazonReturn.amazon_return_id == "RET-001").first()
            ret2 = db.query(AmazonReturn).filter(AmazonReturn.amazon_return_id == "RET-002").first()
            ret4 = db.query(AmazonReturn).filter(AmazonReturn.amazon_return_id == "RET-004").first()
            
            assert ret1 is not None, "RET-001 lost!"
            assert ret2 is not None, "RET-002 lost!"
            assert ret4 is not None, "RET-004 lost!"
            
            print("✅ BATCH FAILURE VERIFIED: Successful records persist, failed record reported, no silent data loss.")
            
    finally:
        # Cleanup
        try:
            db.query(AmazonReturn).filter(AmazonReturn.company_id == company.id).delete()
            db.query(Product).filter(Product.company_id == company.id).delete()
            db.query(Warehouse).filter(Warehouse.company_id == company.id).delete()
            db.query(Company).filter(Company.id == company.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    test_amazon_batch_failure()
