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
    company = Company(name="Amazon Idempotency Co", code="AMZID")
    db.add(company)
    db.flush()
    
    user = User(username="test_amzid", password_hash="hash", role="ADMIN")
    db.add(user)
    db.flush()
    
    wh1 = Warehouse(name="WH1", code="AMZ-WH", company_id=company.id)
    db.add(wh1)
    db.flush()
    
    prod = Product(name="Amazon Item", sku="AMZ-001", company_id=company.id)
    db.add(prod)
    db.commit()
    
    return company, user, wh1, prod

class MockAmazonClient:
    def fetch_returns(self, since=None):
        return [
            {
                "amazon_return_id": "RET-111-222",
                "order_item_id": "ITEM-1",
                "order_id": "ORD-123",
                "seller_sku": "AMZ-001",
                "return_reason": "DEFECTIVE",
                "return_status": "RETURNED",
                "requested_at": "2023-01-01T10:00:00Z",
                "received_at": "2023-01-02T10:00:00Z",
                "quantity": 1
            }
        ]

def test_amazon_return_idempotency():
    db = SessionLocal()
    try:
        print("Setting up amazon returns idempotency test data...")
        company, user, wh1, prod = setup_test_data(db)
        
        with patch.object(ars, 'get_amazon_returns_client', return_value=MockAmazonClient()):
            
            print("Run 1: Syncing returns...")
            created, updated = AmazonReturnsService.sync_returns(db, company.id)
            print(f"Run 1 Results - Created: {created}, Updated: {updated}")
            
            assert created == 1, "Expected 1 record created"
            assert updated == 0, "Expected 0 records updated"
            
            # Verify record exists
            count1 = db.query(AmazonReturn).filter(AmazonReturn.company_id == company.id).count()
            assert count1 == 1, "Expected exactly 1 return record in DB"
            
            print("Run 2: Syncing EXACT SAME returns...")
            created2, updated2 = AmazonReturnsService.sync_returns(db, company.id)
            print(f"Run 2 Results - Created: {created2}, Updated: {updated2}")
            
            assert created2 == 0, "Expected 0 records created (Idempotency check should block creation)"
            assert updated2 == 0, "Expected 0 records updated (Nothing changed)"
            
            # Verify record count is STILL 1
            count2 = db.query(AmazonReturn).filter(AmazonReturn.company_id == company.id).count()
            assert count2 == 1, "Expected exactly 1 return record in DB, duplicates were created!"
            
            print("✅ IDEMPOTENCY VERIFIED: Duplicate Amazon Return records were not created.")
            
    finally:
        # Cleanup
        try:
            db.query(AmazonReturn).filter(AmazonReturn.company_id == company.id).delete()
            db.query(Product).filter(Product.company_id == company.id).delete()
            db.query(Warehouse).filter(Warehouse.company_id == company.id).delete()
            db.query(User).filter(User.id == user.id).delete()
            db.query(Company).filter(Company.id == company.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    test_amazon_return_idempotency()
