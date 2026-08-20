import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import bcrypt

from app.models.db import get_db
from app.models.schema import User
from app.api.dependencies import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

# Rate limit state for password confirmation
# Structure: { user_id: { "count": int, "blocked_until": datetime | None } }
FAILED_ATTEMPTS = {}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    model_config = ConfigDict(from_attributes=True)

import bcrypt

def _hash_password(password: str) -> str:
    # Legacy hash for fallback check
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    if hashed_password.startswith("$2"):
        return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    return hashed_password == _hash_password(plain_password)

def verify_admin_action_password(input_password: Optional[str], current_user: User):
    if not input_password or not input_password.strip():
        raise HTTPException(status_code=400, detail="Admin password required")

    if input_password.strip() == "REQUEST_APPROVAL":
        raise HTTPException(status_code=403, detail="Admin access required")


    state = FAILED_ATTEMPTS.get(current_user.id, {"count": 0, "blocked_until": None})
    
    # Check block
    if state["blocked_until"] and datetime.now() < state["blocked_until"]:
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait 5 minutes.")

    # Verify
    admin_pass = os.environ.get("ADMIN_ACTION_PASSWORD", "masteruser01")
    if input_password.strip() != admin_pass:
        state["count"] += 1
        if state["count"] >= 5:
            state["blocked_until"] = datetime.now() + timedelta(minutes=5)
            state["count"] = 0 # Reset for next cycle
        FAILED_ATTEMPTS[current_user.id] = state
        raise HTTPException(status_code=403, detail="Invalid admin password")

    # Success -> reset
    FAILED_ATTEMPTS[current_user.id] = {"count": 0, "blocked_until": None}
    return True

@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    is_valid = verify_password(credentials.password, user.password_hash)
    needs_upgrade = is_valid and not user.password_hash.startswith("$2")
            
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if needs_upgrade:
        salt = bcrypt.gensalt()
        user.password_hash = bcrypt.hashpw(credentials.password.encode('utf-8')[:72], salt).decode('utf-8')
        db.commit()
    
    token = create_access_token(user)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.username.title(),
            "role": user.role
        }
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.username.title(),
        "role": current_user.role
    }
