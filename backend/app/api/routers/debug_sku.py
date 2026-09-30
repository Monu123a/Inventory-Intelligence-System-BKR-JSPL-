from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.schema import Product

router = APIRouter(tags=["Debug"])

@router.get("/debug-sku")
def debug_sku(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.company_id == 2).all()
    results = []
    for p in products:
        if "TRIMMER" in p.sku.upper() or "168" in p.sku.upper():
            # Get raw hex to see hidden characters
            hex_chars = [hex(ord(c)) for c in p.sku]
            results.append({
                "id": p.id,
                "sku": p.sku,
                "len": len(p.sku),
                "hex": hex_chars,
                "name": p.name
            })
    return {"matches": results}
