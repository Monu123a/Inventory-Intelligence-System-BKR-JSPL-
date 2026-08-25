import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import Company
db = SessionLocal()
companies = db.query(Company).all()
for c in companies:
    print(c.id, c.name, c.status)
