import re

file_path = "backend/app/api/routers/warehouses.py"
with open(file_path, "r") as f:
    content = f.read()

new_endpoint = """
from pydantic import BaseModel
from typing import Optional

class AmazonNetworkUpdate(BaseModel):
    amazon_network: Optional[str] = None # 'MFN', 'AFN', or None

@router.put("/{warehouse_id}/amazon-network", response_model=dict)
def update_amazon_network(
    warehouse_id: int, 
    payload: AmazonNetworkUpdate, 
    company_id: int = Depends(get_current_company_id), 
    db: Session = Depends(get_db), 
    admin_user: User = Depends(require_admin)
):
    from app.models.schema import WarehouseExternalMapping
    
    mapping = db.query(WarehouseExternalMapping).filter(
        WarehouseExternalMapping.warehouse_id == warehouse_id,
        WarehouseExternalMapping.marketplace == "Amazon"
    ).first()
    
    if not mapping:
        mapping = WarehouseExternalMapping(
            warehouse_id=warehouse_id,
            marketplace="Amazon",
            external_code="DEFAULT"
        )
        db.add(mapping)
        
    mapping.amazon_network = payload.amazon_network
    db.commit()
    return {"status": "success", "amazon_network": payload.amazon_network}
"""

if "@router.put(\"/{warehouse_id}/amazon-network\"" not in content:
    content += new_endpoint
    with open(file_path, "w") as f:
        f.write(content)

