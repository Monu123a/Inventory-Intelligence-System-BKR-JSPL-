import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import CompanyUser, User

db = SessionLocal()

user = db.query(User).filter(User.username == 'rubal').first()

if user:
    # Add access to company 2
    if not db.query(CompanyUser).filter(CompanyUser.company_id == 2, CompanyUser.user_id == user.id).first():
        db.add(CompanyUser(company_id=2, user_id=user.id))
    
    # Add access to company 3
    if not db.query(CompanyUser).filter(CompanyUser.company_id == 3, CompanyUser.user_id == user.id).first():
        db.add(CompanyUser(company_id=3, user_id=user.id))
        
    db.commit()
    print("Successfully granted rubal access to companies 2 and 3.")
else:
    print("User rubal not found.")

db.close()
