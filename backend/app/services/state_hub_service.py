from sqlalchemy.orm import Session
from app.models.schema import StateHub

class StateHubService:
    @staticmethod
    def get_all(db: Session, company_id: int):
        return db.query(StateHub).filter(StateHub.company_id == company_id).all()

    @staticmethod
    def get_all_across_companies(db: Session):
        return db.query(StateHub).all()

    @staticmethod
    def get_by_id(db: Session, hub_id: int, company_id: int):
        return db.query(StateHub).filter(StateHub.id == hub_id, StateHub.company_id == company_id).first()

    @staticmethod
    def create(db: Session, company_id: int, data: dict):
        hub = StateHub(company_id=company_id, **data)
        db.add(hub)
        db.flush()
        db.refresh(hub)
        return hub

    @staticmethod
    def update(db: Session, hub_id: int, company_id: int, data: dict):
        hub = StateHubService.get_by_id(db, hub_id, company_id)
        if not hub:
            raise ValueError("State Hub not found")
        for key, value in data.items():
            setattr(hub, key, value)
        db.flush()
        db.refresh(hub)
        return hub

    @staticmethod
    def delete(db: Session, hub_id: int, company_id: int):
        hub = StateHubService.get_by_id(db, hub_id, company_id)
        if not hub:
            raise ValueError("State Hub not found")
        if hub.warehouses:
            raise ValueError("Cannot delete State Hub with assigned warehouses")
        db.delete(hub)
        db.flush()
        return True
