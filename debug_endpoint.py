import sys
import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.models.db import SessionLocal
from app.models.schema import Warehouse, WarehouseExternalMapping, AmazonNetworkType
from sqlalchemy.orm import Session

db = SessionLocal()

warehouse = db.query(Warehouse).first()
if warehouse:
    print(f"Testing for warehouse {warehouse.id}")
    
    mapping = db.query(WarehouseExternalMapping).filter(
        WarehouseExternalMapping.warehouse_id == warehouse.id,
        WarehouseExternalMapping.marketplace == "Amazon"
    ).first()
    
    if not mapping:
        mapping = WarehouseExternalMapping(
            warehouse_id=warehouse.id,
            marketplace="Amazon",
            external_code="DEFAULT"
        )
        db.add(mapping)
        
    try:
        mapping.amazon_network = "MFN"
        db.commit()
        print("Success!")
    except Exception as e:
        print("ERROR:", e)

