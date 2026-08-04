from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.db import get_db
from app.api.dependencies import get_current_company_id
from app.services.state_hub_service import StateHubService

router = APIRouter(prefix="/state-hubs", tags=["State Hubs"])

class StateHubBase(BaseModel):
    hub_code: str
    hub_name: str
    gstin: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "Active"

class StateHubResponse(StateHubBase):
    id: int
    company_id: int
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[StateHubResponse])
def get_state_hubs(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    return StateHubService.get_all(db, company_id)

@router.post("/", response_model=StateHubResponse)
def create_state_hub(hub: StateHubBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        return StateHubService.create(db, company_id, hub.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{hub_id}", response_model=StateHubResponse)
def get_state_hub(hub_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    hub = StateHubService.get_by_id(db, hub_id, company_id)
    if not hub:
        raise HTTPException(status_code=404, detail="State Hub not found")
    return hub

@router.put("/{hub_id}", response_model=StateHubResponse)
def update_state_hub(hub_id: int, hub: StateHubBase, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        return StateHubService.update(db, hub_id, company_id, hub.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{hub_id}")
def delete_state_hub(hub_id: int, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    try:
        StateHubService.delete(db, hub_id, company_id)
        return {"detail": "State Hub deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
