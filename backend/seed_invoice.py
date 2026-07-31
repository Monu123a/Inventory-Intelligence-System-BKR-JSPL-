import sys
from pathlib import Path
from datetime import datetime

# Setup paths to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.db import SessionLocal
from app.models.schema import Company, Product, Inventory, Warehouse, Sale, SaleItem

def seed_dummy_invoice():
    db = SessionLocal()
    try:
        # 1. Get or Create Company
        company = db.query(Company).filter(Company.code == "BKR").first()
        if not company:
            company = Company(name="BKR Solutions", code="BKR", status="Active")
            db.add(company)
            db.flush()

        # 2. Get or Create Product
        product = db.query(Product).filter(Product.sku == "SAMPLE-001").first()
        if not product:
            product = Product(
                company_id=company.id,
                sku="SAMPLE-001",
                name="Premium Steel Pipe 20mm",
                item_rate=500.0,
                default_gst_rate=18.0,
                hsn_code="7304",
                unit="PCS"
            )
            db.add(product)
            db.flush()

        # 3. Create a Dummy Sale
        sale = Sale(
            bill_number="BILL-MOCK-001",
            company_id=company.id,
            invoice_number="BKR/26-27/MOCK-001",
            invoice_type="B2B",
            customer_name="Acme Corporation",
            customer_gstin="27BBBBB0000B1Z5",
            customer_address="45 Industrial Estate, Pune",
            customer_state="Maharashtra",
            customer_state_code="27",
            place_of_supply="Maharashtra",
            customer_email="billing@acme.com",
            customer_phone="9876543210",
            total_taxable_amount=50000.0,
            total_tax=9000.0,
            grand_total=59000.0,
            payment_method="UPI",
            payment_reference="UPI99887766",
            payment_date=datetime.utcnow(),
            status="Completed",
            tally_sync_status="PENDING",
            
            # Snapshots
            company_name_snapshot="BKR Solutions Pvt Ltd",
            company_gstin_snapshot="27AAAAA0000A1Z5",
            company_address_snapshot="123 Tech Park, Sector 4, Maharashtra",
            company_state_snapshot="Maharashtra",
            company_state_code_snapshot="27",
            company_email_snapshot="billing@bkrsolutions.com",
            company_phone_snapshot="+91 9876543210",
            
            # Transport
            payment_terms="Net 30",
            delivery_note="Delivery via truck",
            dispatch_through="Road",
            destination="Pune",
            vehicle_number="MH-12-AB-1234"
        )
        db.add(sale)
        db.flush()

        # 4. Create Sale Item
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            sku=product.sku,
            product_name=product.name,
            hsn_sac=product.hsn_code,
            unit=product.unit,
            quantity=100,
            selling_price=500.0,
            discount=0.0,
            gst_rate=18.0,
            taxable_amount=50000.0,
            cgst=4500.0,
            sgst=4500.0,
            igst=0.0,
            line_total=59000.0
        )
        db.add(sale_item)
        db.commit()
        
        print(f"Success! Generated Dummy Invoice ID: {sale.id}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_dummy_invoice()
