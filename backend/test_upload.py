import sys
import os
import pandas as pd
sys.path.append(os.getcwd())

from app.models.db import SessionLocal
from app.services.inventory_adapter import InventoryAdapter
from app.services.inventory_validation import InventoryValidationService

with open("test_upload.csv", "w") as f:
    f.write("sku,warehouse_name,quantity\nLG0314,B K RAMAN AND CO (Formerly Jagan Hardware),1\nLG0648,B K RAMAN AND CO (Formerly Jagan Hardware),10\n")

db = SessionLocal()
parsed = InventoryAdapter.parse_inventory_file("test_upload.csv")
print("Parsed:", parsed)

# BKR Company ID is usually 2 or something. Let's find a valid warehouse for BKR.
from app.models.schema import Warehouse, Company
company = db.query(Company).filter(Company.code == 'BKR').first()
warehouse = db.query(Warehouse).filter(Warehouse.company_id == company.id).first()

if warehouse:
    print(f"Testing with warehouse {warehouse.code} in company {company.id}")
    is_valid, valid_records, errors = InventoryValidationService.validate_upload(db, parsed, warehouse.code, company.id)
    print("Is Valid:", is_valid)
    print("Errors:", errors)
else:
    print("No warehouse found.")
