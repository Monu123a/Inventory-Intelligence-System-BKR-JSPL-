import sys
import os
import bcrypt

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import User

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
    new_user = User(
        username=username,
        password_hash=hash_password(password),
        role="Admin"  # Defaulting to Admin, adjust if needed
    )
    db.add(new_user)
    db.commit()
    print(f"Successfully created user {username}")

db.close()
