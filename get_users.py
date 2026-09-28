import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import User
db = SessionLocal()
for u in db.query(User).all():
    print(u.username, u.role, u.password_hash)
