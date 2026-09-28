import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"ID: {u.id}, Username: {u.username}, Role: {u.role}, Hash: {u.password_hash}")
db.close()
