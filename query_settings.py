import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import CompanySettings, Company
db = SessionLocal()
companies = db.query(Company).all()
for c in companies:
    s = db.query(CompanySettings).filter(CompanySettings.company_id == c.id).first()
    if s:
        print(f"Company {c.name}: legal_name='{s.legal_name}', gstin='{s.gstin}', address='{s.address}'")
    else:
        print(f"Company {c.name} has NO settings.")
