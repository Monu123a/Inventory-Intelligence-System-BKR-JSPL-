import sys
import os
from datetime import datetime, timedelta

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.db import SessionLocal
from app.models.schema import AmazonReturn, Company

def seed_returns():
    db = SessionLocal()
    
    # Get a company (assume company 1 for JSPL)
    company = db.query(Company).first()
    if not company:
        print("No company found.")
        return
        
    company_id = company.id

    returns = [
        AmazonReturn(
            company_id=company_id,
            amazon_return_id="RET-AMZ-1001",
            amazon_order_id="112-9988776-5544331",
            order_item_id="ITEM-001",
            sku="TMT-10MM-JSPL",
            product_name="Jindal Panther TMT Rebar 10mm",
            quantity=2,
            return_reason="Wrong item sent",
            return_status="In Transit",
            requested_at=datetime.utcnow() - timedelta(days=3)
        ),
        AmazonReturn(
            company_id=company_id,
            amazon_return_id="RET-AMZ-1002",
            amazon_order_id="112-9988776-5544332",
            order_item_id="ITEM-002",
            sku="CEMENT-PPC-50",
            product_name="JSW Cement PPC 50kg Bag",
            quantity=5,
            return_reason="Damaged during transit",
            return_status="Received",
            requested_at=datetime.utcnow() - timedelta(days=2),
            received_at=datetime.utcnow() - timedelta(hours=5)
        ),
        AmazonReturn(
            company_id=company_id,
            amazon_return_id="RET-AMZ-1003",
            amazon_order_id="112-9988776-5544333",
            order_item_id="ITEM-003",
            sku="PAINT-ASIAN-20L",
            product_name="Asian Paints Apex 20L",
            quantity=1,
            return_reason="Customer cancelled",
            return_status="Received",
            requested_at=datetime.utcnow() - timedelta(days=1),
            received_at=datetime.utcnow() - timedelta(hours=1)
        ),
        AmazonReturn(
            company_id=company_id,
            amazon_return_id="RET-AMZ-1004",
            amazon_order_id="112-9988776-5544334",
            order_item_id="ITEM-004",
            sku="SWITCH-ANCHOR-10",
            product_name="Anchor ROMA Switch 10A",
            quantity=10,
            return_reason="Not needed anymore",
            return_status="In Transit",
            requested_at=datetime.utcnow()
        )
    ]
    
    for r in returns:
        # Check if exists first to avoid unique constraint failure
        existing = db.query(AmazonReturn).filter(AmazonReturn.amazon_return_id == r.amazon_return_id).first()
        if not existing:
            db.add(r)
        
    db.commit()
    print("Successfully created mock Amazon Returns.")

if __name__ == "__main__":
    seed_returns()
