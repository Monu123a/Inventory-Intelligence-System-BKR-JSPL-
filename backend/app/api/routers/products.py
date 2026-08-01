from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.db import get_db
from app.models.schema import Product
from app.api.dependencies import get_current_company_id

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
    hsn_code: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    reorder_level: Optional[int] = None
    safety_stock: Optional[int] = None
    default_gst_rate: Optional[float] = None

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

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.sku == product.sku, Product.company_id == company_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    new_prod = Product(**product.model_dump(), company_id=company_id)
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)
    return new_prod

@router.get("/{sku}", response_model=ProductResponse)
def get_product(sku: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{sku}", response_model=ProductResponse)
def update_product(sku: str, product: ProductCreate, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)
        
    db.commit()
    db.refresh(existing)
    return existing

@router.delete("/{sku}")
def delete_product(sku: str, company_id: int = Depends(get_current_company_id), db: Session = Depends(get_db)):
    from app.models.schema import Inventory, InventoryMovement
    
    existing = db.query(Product).filter(Product.sku == sku, Product.company_id == company_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Check for historical dependencies before allowing hard delete
    has_inventory = db.query(Inventory).filter(Inventory.product_id == existing.id).first()
    has_movements = db.query(InventoryMovement).filter(InventoryMovement.product_id == existing.id).first()
    
    if has_inventory or has_movements:
        raise HTTPException(
            status_code=400, 
            detail="Cannot hard-delete this product because it has historical inventory or order records. Please Deactivate it instead."
        )
        
    db.delete(existing)
    db.commit()
    return {"message": "Product deleted successfully"}
