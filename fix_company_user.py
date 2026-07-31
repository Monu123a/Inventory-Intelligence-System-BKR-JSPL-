import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.db import engine, Base, SessionLocal
from app.models.schema import User, Company, CompanyUser

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Ensure user 1 exists
user = db.query(User).filter(User.id == 1).first()
if not user:
    import hashlib
    pw_hash = hashlib.sha256("admin".encode()).hexdigest()
    user = User(id=1, username="admin", password_hash=pw_hash, role="admin")
    db.add(user)
    db.commit()

# Ensure companies exist
companies = db.query(Company).all()
if not companies:
    print("No companies found!")
else:
    for c in companies:
        cu = db.query(CompanyUser).filter(CompanyUser.user_id == 1, CompanyUser.company_id == c.id).first()
        if not cu:
            print(f"Mapping user 1 to company {c.code}")
            new_cu = CompanyUser(user_id=1, company_id=c.id, role="admin")
            db.add(new_cu)
    
    db.commit()
    print("User mapped to all companies.")

db.close()
