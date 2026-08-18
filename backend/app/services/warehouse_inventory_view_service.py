from sqlalchemy.orm import Session
from typing import Optional
from app.models.schema import Inventory, Product

class WarehouseInventoryViewService:
    @staticmethod
    def get_inventory_view(db: Session, company_id: int, warehouse_id: Optional[int] = None, category: Optional[str] = None, sku: Optional[str] = None):
        query = db.query(Inventory).join(Product).filter(Inventory.company_id == company_id)

        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        if sku:
            query = query.filter(Product.sku.ilike(f"%{sku}%"))

        return query.all()
