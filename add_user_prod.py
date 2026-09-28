import sys
import os
import bcrypt

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import User
from sqlalchemy import func

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8')[:72], salt)
    return hashed.decode('utf-8')

db = SessionLocal()

username = "rubal"
password = "userrubal"

existing_user = db.query(User).filter(User.username == username).first()

if existing_user:
    print(f"User {username} already exists.")
else:
    # Explicitly calculate next ID to bypass sequence desync
    max_id = db.query(func.max(User.id)).scalar() or 0
    
    new_user = User(
        id=max_id + 1,
        username=username,
        password_hash=hash_password(password),
        role="Admin"
    )
    db.add(new_user)
    db.commit()
    print(f"Successfully created user {username} with id {max_id + 1}")

db.close()
