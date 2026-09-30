from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.schema import Warehouse, Inventory, Product

router = APIRouter(tags=["Debug"])

@router.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):
    whs = db.query(Warehouse).filter(Warehouse.company_id == 2).all()
    invs = db.query(Inventory).filter(Inventory.company_id == 2).all()
    prods = db.query(Product).filter(Product.company_id == 2).all()
    
    return {
        "warehouses": [{"id": w.id, "code": w.code, "name": w.name} for w in whs],
        "inventory": [{"id": i.id, "product_id": i.product_id, "warehouse_id": i.warehouse_id, "qty": i.current_qty} for i in invs],
        "products_count": len(prods),
        "trimmer_products": [{"id": p.id, "sku": p.sku} for p in prods if "TRIMMER" in p.sku.upper()]
    }
