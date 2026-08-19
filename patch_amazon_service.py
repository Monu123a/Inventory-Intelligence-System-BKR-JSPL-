with open("backend/app/services/amazon_service.py", "r") as f:
    content = f.read()

old_logic = """                    fc_code = order.get("fulfillment_center")
                    
                    if not fc_code:
                        raise ValueError("No fulfillment center in order")
                        
                    # Lookup External Mapping
                    mapping = db.query(WarehouseExternalMapping).filter(
                        WarehouseExternalMapping.marketplace == "Amazon",
                        WarehouseExternalMapping.external_code == fc_code
                    ).first()
                    
                    if not mapping:
                        # Log to quarantine
                        sync_log = AmazonSyncLog(
                            company_id=company_id, 
                            order_id=order_id, 
                            status="Quarantined", 
                            errors="Needs Mapping",
                            unknown_skus=f'["{fc_code}"]' # Hack to store FC code for UI for now
                        )
                        db.add(sync_log)
                        skipped_count += 1
                        continue
                        
                    warehouse_id = mapping.warehouse_id"""

new_logic = """                    fc_code = order.get("fulfillment_center")
                    warehouse_id = None
                    
                    if fc_code:
                        # Lookup External Mapping if fc_code is present
                        from app.models.schema import WarehouseExternalMapping
                        mapping = db.query(WarehouseExternalMapping).filter(
                            WarehouseExternalMapping.marketplace == "Amazon",
                            WarehouseExternalMapping.external_code == fc_code
                        ).first()
                        if mapping:
                            warehouse_id = mapping.warehouse_id
                    
                    if not warehouse_id:
                        # Fallback to JSPL Central Warehouse if FC code is missing or unmapped
                        from app.models.schema import Warehouse
                        central_wh = db.query(Warehouse).filter(
                            Warehouse.company_id == company_id,
                            Warehouse.name.ilike('%Central%')
                        ).first()
                        
                        if not central_wh:
                            raise ValueError("No Central warehouse found for fallback")
                            
                        warehouse_id = central_wh.id"""

content = content.replace(old_logic, new_logic)

with open("backend/app/services/amazon_service.py", "w") as f:
    f.write(content)
