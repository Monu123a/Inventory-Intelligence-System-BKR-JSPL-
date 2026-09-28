import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import CompanyUser

db = SessionLocal()
mappings = db.query(CompanyUser).all()
for m in mappings:
    print(f"Company ID: {m.company_id}, User ID: {m.user_id}")
db.close()
