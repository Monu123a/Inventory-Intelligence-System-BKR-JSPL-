import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Company, CompanySettings, CompanyUser
from sqlalchemy import func
db = SessionLocal()

companies = db.query(Company).filter(func.lower(Company.status) == "active").all()
print([c.name for c in companies])
