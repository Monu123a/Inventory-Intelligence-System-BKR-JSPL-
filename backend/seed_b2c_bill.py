import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import Company, User, Product, Sale, SaleItem, CompanySettings
from app.models.db import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Find BKR company
company = db.query(Company).filter(Company.name.ilike('%BKR%')).first()
if not company:
    company = db.query(Company).first()

if not company:
    print("No company found.")
    sys.exit(1)

# Ensure company settings exist
settings = db.query(CompanySettings).filter(CompanySettings.company_id == company.id).first()
if not settings:
    settings = CompanySettings(
        company_id=company.id,
        legal_name="BKR Group Private Limited",
        gstin="07AAAAA0000A1Z5",
        address="123 Corporate Road, Tech Park",
        state="Delhi",
        state_code="07",
        email="billing@bkrgroup.com",
        phone="+91-9876543210",
        declaration="We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct."
    )
    db.add(settings)
    db.commit()

# Find some products
products = db.query(Product).filter(Product.company_id == company.id).limit(3).all()
if not products:
    print("No products found for this company. Please add products first.")
    sys.exit(1)

# Create a B2C Sale
from app.services.invoice_number_service import InvoiceNumberService
try:
    bill_no, inv_no = InvoiceNumberService.generate_next_numbers(db, company.id)
except Exception as e:
    bill_no = f"BLL-B2C-{datetime.now().strftime('%H%M%S')}"
    inv_no = f"INV-B2C-{datetime.now().strftime('%H%M%S')}"

new_sale = Sale(
    bill_number=bill_no,
    company_id=company.id,
    customer_name="John Doe (Walk-in)",
    customer_mobile="9876543210",
    sale_date=datetime.now(timezone.utc),
    payment_method="UPI",
    payment_reference="UPI-1234567890",
    status="Completed",
    invoice_number=inv_no,
    invoice_type="B2C",
    customer_state="Delhi",
    customer_state_code="07",
    place_of_supply="07-Delhi"
)
db.add(new_sale)
db.flush()

total_taxable = 0.0
total_tax = 0.0
total_grand = 0.0

for prod in products:
    qty = 2
    rate = prod.item_rate or 1500.0
    gst_rate = prod.default_gst_rate or 18.0
    
    # Calculate tax assuming intra-state (CGST + SGST)
    taxable_val = qty * rate
    tax_amt = (taxable_val * gst_rate) / 100.0
    line_total = taxable_val + tax_amt
    
    cgst = tax_amt / 2
    sgst = tax_amt / 2
    igst = 0.0

    item = SaleItem(
        sale_id=new_sale.id,
        product_id=prod.id,
        sku=prod.sku,
        quantity=qty,
        selling_price=rate,
        gst_rate=gst_rate,
        taxable_amount=taxable_val,
        cgst=cgst,
        sgst=sgst,
        igst=igst,
        line_total=line_total,
        product_name=prod.name,
        hsn_sac=prod.hsn_code,
        unit="NOS",
        discount=0.0
    )
    db.add(item)
    
    total_taxable += taxable_val
    total_tax += tax_amt
    total_grand += line_total

new_sale.total_taxable_amount = total_taxable
new_sale.total_tax = total_tax
new_sale.grand_total = total_grand

db.commit()
print(f"Success! Generated B2C Bill: {bill_no} / Invoice: {inv_no}")
