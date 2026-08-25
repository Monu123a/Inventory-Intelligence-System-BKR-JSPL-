import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Company, CompanySettings
db = SessionLocal()

comps = db.query(Company).all()
for c in comps:
    print(c.id, c.name, c.status)
    s = db.query(CompanySettings).filter(CompanySettings.company_id == c.id).first()
    if s:
        print("  ->", s.legal_name, s.address, s.gstin)
    else:
        print("  -> NO SETTINGS")
