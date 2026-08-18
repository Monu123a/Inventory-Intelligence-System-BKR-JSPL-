from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import logging
from datetime import datetime

from app.models.db import get_db
from app.models.schema import User, CompanyUser
from app.api.dependencies import get_current_company_id, require_admin
from app.api.routers.auth import verify_admin_action_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

class UserCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    role: str = "TECHNICIAN"
    admin_password: Optional[str] = Field(default=None, exclude=True)

class UserResponse(BaseModel):
    id: int
    full_name: str
    username: str
    role: str

@router.post("/", response_model=UserResponse, dependencies=[Depends(require_admin)])
def create_user(user_data: UserCreate, company_id: int = Depends(get_current_company_id), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Verify admin password
    verify_admin_action_password(user_data.admin_password, current_user)
    
    # Create a unique username for the technician
    # We use a suffix to prevent cross-company collisions
    clean_name = user_data.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Name is required")

    base_username = f"tech_{clean_name.replace(' ', '_').lower()}_{company_id}"
    
    # Check for duplicates within the company
    # Technicians have the same base username if they have the same name in the same company
    existing_user = db.query(User).join(CompanyUser).filter(
        User.username == base_username,
        CompanyUser.company_id == company_id
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="A technician with this name already exists in your company")

    # If phone is provided, we could append it or just ignore it since DB has no phone column
    # For now, we keep it simple as requested.
    
    # Create the user with a dummy password
    new_user = User(
        username=base_username,
        password_hash=f"$2b$12${uuid.uuid4().hex}",  # Dummy secure hash
        role=user_data.role
    )
    
    db.add(new_user)
    db.flush() # To get new_user.id
    
    # Assign to company
    company_user = CompanyUser(
        user_id=new_user.id,
        company_id=company_id,
        role=user_data.role
    )
    db.add(company_user)
    
    try:
        db.commit()
        logger.info({
            "action": "CREATE_USER",
            "user_id": current_user.id,
            "company_id": company_id,
            "target_user_id": new_user.id,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create user")
        
    return {
        "id": new_user.id,
        "full_name": clean_name,
        "username": base_username,
        "role": user_data.role
    }

@router.get("/", response_model=List[UserResponse])
def get_users(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    # Fetch all users for the current company
    users = db.query(User).join(CompanyUser).filter(
        CompanyUser.company_id == company_id
    ).all()
    
    result = []
    for u in users:
        # Extract full name from the tech format if it is a tech
        if u.username.startswith("tech_") and f"_{company_id}" in u.username:
            name_part = u.username.replace("tech_", "").replace(f"_{company_id}", "").replace("_", " ").title()
        else:
            name_part = u.username.title()
            
        result.append({
            "id": u.id,
            "full_name": name_part,
            "username": u.username,
            "role": u.role
        })
        
    return result
