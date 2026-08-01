from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.schema import Product, Warehouse
import logging

logger = logging.getLogger("inventory.validation_service")

class InventoryValidationService:
    
    @staticmethod
    def validate_upload(db: Session, records: List[Dict[str, Any]], warehouse_code: str, company_id: int) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """
        Validates inventory upload records before they reach the Event Engine.
        Returns:
            - is_valid (bool)
            - valid_records (list of dicts)
            - errors (list of strings)
        """
        errors = []
        valid_records = []
        
        # Validate warehouse
        warehouse = db.query(Warehouse).filter(Warehouse.code == warehouse_code, Warehouse.company_id == company_id).first()
        if not warehouse:
            errors.append(f"Invalid warehouse code: {warehouse_code}")
            return False, [], errors

        # Cache existing SKUs for fast lookup
        existing_skus = {p.sku for p in db.query(Product.sku).filter(Product.company_id == company_id).all()}
        
        seen_skus = set()
        
        for idx, record in enumerate(records):
            sku = record.get("sku")
            quantity = record.get("quantity")
            
            row_num = idx + 2 # Excel row logic (header is row 1)
            
            if not sku:
                errors.append(f"Row {row_num}: Missing SKU.")
                continue
                
            if sku in seen_skus:
                errors.append(f"Row {row_num}: Duplicate SKU in upload file ({sku}).")
                continue
            seen_skus.add(sku)
            
            if sku not in existing_skus:
                # We could auto-create a placeholder, but validation highlights it.
                # Depending on business logic, we might warn or block.
                # The user asked for "SKU exists" as a validation check.
                errors.append(f"Row {row_num}: SKU {sku} does not exist in Product Master.")
                continue
                
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: Quantity for SKU {sku} is not numeric.")
                continue
            
            if quantity < 0:
                errors.append(f"Row {row_num}: Quantity for SKU {sku} cannot be negative ({quantity}).")
                continue
                
            record["warehouse_id"] = warehouse.id
            valid_records.append(record)
            
        is_valid = len(errors) == 0
        return is_valid, valid_records, errors
