import hashlib

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.models.db import get_db
from app.models.schema import Company, CompanyUser, User


def _build_token(user: User) -> str:
    return hashlib.sha256(f"{user.id}:{user.username}:secret".encode()).hexdigest()


def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer auth token"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    users = db.query(User).all()
    for user in users:
        if _build_token(user) == token:
            return user

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
    company = db.query(Company).filter(Company.id == company_id, Company.status == "Active").first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found or inactive")

    access = db.query(CompanyUser).filter(
        CompanyUser.user_id == current_user.id,
        CompanyUser.company_id == company_id
    ).first()
    if not access:
        raise HTTPException(status_code=403, detail="You do not have permission to access this company")

    return company_id
