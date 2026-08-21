from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
import logging
from datetime import datetime

from app.models.db import get_db
from app.models.schema import Product
from app.api.dependencies import get_current_company_id, require_admin
from app.api.routers.auth import verify_admin_action_password
from app.services.audit_log_service import AuditLogService
from app.models.schema import Inventory, InventoryMovement, SaleItem, SalesReturnItem, DeliveryChallanItem, StockTransferItem, ServiceRecordItem, User, DamageClaim, DefectiveInventory, FCDispatchItem, FCReturnItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])

class ProductCreate(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    item_rate: float = 0.0
    min_stock_level: int = 0
    status: str = "Active"
    hsn: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    reorder_level: Optional[int] = None
    safety_stock: Optional[int] = None
    default_gst_rate: Optional[float] = None
    admin_password: Optional[str] = Field(default=None, exclude=True)

class ProductResponse(ProductCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

@router.get("/filters")
def get_product_filters(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    categories = [r[0] for r in db.query(Product.category).filter(Product.company_id == company_id).distinct().all() if r[0]]
    brands = [r[0] for r in db.query(Product.brand).filter(Product.company_id == company_id).distinct().all() if r[0]]
    return {"categories": categories, "brands": brands}

@router.get("/", response_model=List[ProductResponse])
def get_products(company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.company_id == company_id).all()

@router.post("/", response_model=ProductResponse, dependencies=[Depends(require_admin)])
def create_product(product: ProductCreate, company_id: int = Depends(get_current_company_id), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    verify_admin_action_password(product.admin_password, current_user)
    existing = db.query(Product).filter(Product.sku == product.sku, Product.company_id == company_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    new_prod = Product(**product.model_dump(), company_id=company_id)
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)
    logger.info({
        "action": "CREATE_PRODUCT",
        "user_id": current_user.id,
        "company_id": company_id,
        "sku": product.sku,
        "timestamp": datetime.utcnow().isoformat()
    })
    return new_prod

@router.get("/{sku}", response_model=ProductResponse)
def get_product(sku: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{sku}", response_model=ProductResponse, dependencies=[Depends(require_admin)])
def update_product(sku: str, product: ProductCreate, company_id: int = Depends(get_current_company_id), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    verify_admin_action_password(product.admin_password, current_user)
    existing = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.sku != sku:
        check_dup = db.query(Product).filter(Product.sku == product.sku, Product.company_id == company_id).first()
        if check_dup:
            raise HTTPException(status_code=400, detail="Cannot change SKU to one that already exists")
    
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)
        
    db.commit()
    db.refresh(existing)
    logger.info({
        "action": "UPDATE_PRODUCT",
        "user_id": current_user.id,
        "company_id": company_id,
        "sku": sku,
        "timestamp": datetime.utcnow().isoformat()
    })
    return existing

class DeleteRequest(BaseModel):
    admin_password: Optional[str] = Field(default=None)

@router.delete("/{sku}", dependencies=[Depends(require_admin)])
def delete_product(sku: str, payload: DeleteRequest, company_id: int = Depends(get_current_company_id), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    verify_admin_action_password(payload.admin_password, current_user)
    
    existing = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Check for historical dependencies before allowing hard delete
    has_inventory = db.query(Inventory).filter(Inventory.product_id == existing.id).first()
    has_movements = db.query(InventoryMovement).filter(InventoryMovement.product_id == existing.id).first()
    has_sales = db.query(SaleItem).filter(SaleItem.product_id == existing.id).first()
    has_returns = db.query(SalesReturnItem).filter(SalesReturnItem.product_id == existing.id).first()
    has_challans = db.query(DeliveryChallanItem).filter(DeliveryChallanItem.product_id == existing.id).first()
    has_transfers = db.query(StockTransferItem).filter(StockTransferItem.product_id == existing.id).first()
    has_services = db.query(ServiceRecordItem).filter(ServiceRecordItem.product_id == existing.id).first()
    has_damage = db.query(DamageClaim).filter(DamageClaim.product_id == existing.id).first()
    has_defective = db.query(DefectiveInventory).filter(DefectiveInventory.product_id == existing.id).first()
    has_fcdispatch = db.query(FCDispatchItem).filter(FCDispatchItem.product_id == existing.id).first()
    has_fcreturn = db.query(FCReturnItem).filter(FCReturnItem.product_id == existing.id).first()
    
    if any([has_inventory, has_movements, has_sales, has_returns, has_challans, has_transfers, has_services, has_damage, has_defective, has_fcdispatch, has_fcreturn]):
        raise HTTPException(
            status_code=400, 
            detail="Cannot hard-delete this product because it has historical inventory or order records (Sales, Returns, Challans, etc). Please Deactivate it instead."
        )
        
    AuditLogService.log(
        db,
        company_id=company_id,
        entity_type="Product",
        entity_id=existing.id,
        event_type="PRODUCT_DELETED",
        message=f"Product {existing.sku} ({existing.name}) deleted",
        metadata={"sku": existing.sku, "name": existing.name}
    )
        
    db.delete(existing)
    db.commit()
    logger.info({
        "action": "DELETE_PRODUCT",
        "user_id": current_user.id,
        "company_id": company_id,
        "sku": sku,
        "timestamp": datetime.utcnow().isoformat()
    })
    return {"detail": "Product deactivated successfully"}
