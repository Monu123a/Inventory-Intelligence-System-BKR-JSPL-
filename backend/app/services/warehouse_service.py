from sqlalchemy.orm import Session
from app.models.schema import Warehouse, WarehouseUser
from app.models.schema import FCDispatch, FCReturn
from app.models.schema import WarehouseExternalMapping

class WarehouseService:
@staticmethod
    def get_all(db: Session, company_id: int):
        return db.query(Warehouse).filter(Warehouse.company_id == company_id).all()

    @staticmethod
    def get_all_across_companies(db: Session):
        return db.query(Warehouse).all()

    @staticmethod
    def get_by_id(db: Session, warehouse_id: int, company_id: int):
        return db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.company_id == company_id).first()

    @staticmethod
    def create(db: Session, company_id: int, data: dict):
        mappings = data.pop("external_mappings", [])
        warehouse = Warehouse(company_id=company_id, **data)
        db.add(warehouse)
        
        for m in mappings:
            mapping = WarehouseExternalMapping(
                warehouse=warehouse,
                marketplace=m["marketplace"],
                external_code=m["external_code"]
            )
            db.add(mapping)
            
        db.flush()
        db.refresh(warehouse)
        return warehouse

    @staticmethod
    def update(db: Session, warehouse_id: int, company_id: int, data: dict):
        warehouse = WarehouseService.get_by_id(db, warehouse_id, company_id)
        if not warehouse:
            raise ValueError("Warehouse not found")
            
        mappings = data.pop("external_mappings", None)
        
        for key, value in data.items():
            setattr(warehouse, key, value)
            
        if mappings is not None:
            db.query(WarehouseExternalMapping).filter(WarehouseExternalMapping.warehouse_id == warehouse.id).delete()
            for m in mappings:
                mapping = WarehouseExternalMapping(
                    warehouse_id=warehouse.id,
                    marketplace=m["marketplace"],
                    external_code=m["external_code"]
                )
                db.add(mapping)
                
        db.flush()
        db.refresh(warehouse)
        return warehouse

    @staticmethod
    def delete(db: Session, warehouse_id: int, company_id: int):
        
        warehouse = WarehouseService.get_by_id(db, warehouse_id, company_id)
        if not warehouse:
            raise ValueError("Warehouse not found")
        # Ensure it has no inventory before deleting
        if warehouse.inventories:
            raise ValueError("Cannot delete warehouse with inventory")
        
        # Ensure it has no FC Dispatches
        dispatches = db.query(FCDispatch).filter(FCDispatch.warehouse_id == warehouse_id).first()
        if dispatches:
            raise ValueError("Cannot delete warehouse with linked FC Dispatches")
            
        # Ensure it has no FC Returns
        returns = db.query(FCReturn).filter(FCReturn.warehouse_id == warehouse_id).first()
        if returns:
            raise ValueError("Cannot delete warehouse with linked FC Returns")

        db.delete(warehouse)
        db.flush()
        return True

    @staticmethod
    def get_warehouse_users(db: Session, warehouse_id: int):
        return db.query(WarehouseUser).filter(WarehouseUser.warehouse_id == warehouse_id).all()

    @staticmethod
    def assign_warehouse_user(db: Session, warehouse_id: int, user_id: int, permission: str = "VIEW"):
        existing = db.query(WarehouseUser).filter(
            WarehouseUser.warehouse_id == warehouse_id,
            WarehouseUser.user_id == user_id
        ).first()
        if existing:
            existing.permission = permission
        else:
            existing = WarehouseUser(warehouse_id=warehouse_id, user_id=user_id, permission=permission)
            db.add(existing)
        db.flush()
        db.refresh(existing)
        return existing

    @staticmethod
    def remove_warehouse_user(db: Session, warehouse_id: int, user_id: int):
        existing = db.query(WarehouseUser).filter(
            WarehouseUser.warehouse_id == warehouse_id,
            WarehouseUser.user_id == user_id
        ).first()
        if existing:
            db.delete(existing)
            db.flush()
            return True
        return False
