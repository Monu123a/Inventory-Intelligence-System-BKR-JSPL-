from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.schema import Product

router = APIRouter(tags=["Fix"])

@router.get("/fix-sku")
def fix_sku(db: Session = Depends(get_db)):
    # Check if TRIMMERLINE168MTR exists for company 2
    p = db.query(Product).filter(Product.sku == "TRIMMERLINE168MTR", Product.company_id == 2).first()
    if p:
        return {"message": f"Already exists with ID {p.id} in DB"}
    
    # Create it
    new_product = Product(
        company_id=2, # BKR
        sku="TRIMMERLINE168MTR",
        name="Trimmer Line 168 MTR",
        category="Accessories",
        unit="Pieces",
        item_rate=0.0,
        status="Active",
        hsn="82089090",
        default_gst_rate=18.0
    )
    db.add(new_product)
    db.commit()
    return {"message": "Created successfully"}
