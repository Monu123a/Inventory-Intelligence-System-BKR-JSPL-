from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
import hashlib

from app.models.db import get_db
from app.models.schema import User
from app.api.dependencies import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

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

@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if the stored hash is bcrypt or legacy
    is_valid = False
    needs_upgrade = False
    
    if user.password_hash.startswith("$2"):
        # Use bcrypt directly
        is_valid = bcrypt.checkpw(credentials.password.encode('utf-8')[:72], user.password_hash.encode('utf-8'))
    else:
        # Fallback to legacy check
        if user.password_hash == _hash_password(credentials.password):
            is_valid = True
            needs_upgrade = True
            
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
