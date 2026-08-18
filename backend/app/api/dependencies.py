import os
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.models.db import get_db
from app.models.schema import Company, CompanyUser, User

import jwt


JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def _get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "your-super-secret-key-change-in-prod")


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])

def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer auth token"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    try:
        payload = decode_access_token(token)
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    except jwt.PyJWTError:
        pass
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Authentication is not configured")

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_company_id(
    x_company_id: Optional[str] = Header(None, description="ID of the selected company"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> int:
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header is missing")
    
    try:
        company_id = int(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Company-Id must be an integer")

    # Validate that company exists
    from sqlalchemy import func
    company = db.query(Company).filter(Company.id == company_id, func.lower(Company.status) == "active").first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found or inactive")

    access = db.query(CompanyUser).filter(
        CompanyUser.user_id == current_user.id,
        CompanyUser.company_id == company_id
    ).first()
    if not access:
        raise HTTPException(status_code=403, detail="You do not have permission to access this company")

    return company_id

def require_admin(
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    is_admin = False
    
    # Check if user is global Admin or Super Admin
    if current_user.role.upper() in ["ADMIN", "SUPER_ADMIN"]:
        is_admin = True
    else:
        # Check if user is Admin for this specific company
        company_access = db.query(CompanyUser).filter(
            CompanyUser.user_id == current_user.id,
            CompanyUser.company_id == company_id
        ).first()
        
        if company_access and company_access.role and company_access.role.upper() in ["ADMIN", "SUPER_ADMIN"]:
            is_admin = True
            
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")

    return current_user

def require_manager(
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    # Check if user is global Admin/Super Admin/Manager
    if current_user.role.upper() in ["ADMIN", "SUPER_ADMIN", "MANAGER"]:
        return current_user
        
    # Check if user has required role for this specific company
    company_access = db.query(CompanyUser).filter(
        CompanyUser.user_id == current_user.id,
        CompanyUser.company_id == company_id
    ).first()
    
    if company_access and company_access.role and company_access.role.upper() in ["ADMIN", "SUPER_ADMIN", "MANAGER"]:
        return current_user
        
    raise HTTPException(status_code=403, detail="Not authorized. Manager or Admin access required.")
