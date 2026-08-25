import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import CompanySettings, Company
db = SessionLocal()

bkr = db.query(Company).filter(Company.code == 'BKR').first()
if bkr:
    s = db.query(CompanySettings).filter(CompanySettings.company_id == bkr.id).first()
    if not s:
        s = CompanySettings(company_id=bkr.id)
        db.add(s)
    s.legal_name = 'B K RAMAN AND CO (Formerly Jagan Hardware)'
    s.gstin = '04AABCU9603R1ZM'
    s.address = 'Industrial Area, Phase 1, Chandigarh'
    s.state = 'Chandigarh'
    s.state_code = '04'
    db.commit()
    print("BKR settings updated!")

