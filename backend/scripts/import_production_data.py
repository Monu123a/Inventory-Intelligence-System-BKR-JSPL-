import os
import sys
import csv
import json
from datetime import datetime

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.db import SessionLocal, Base, engine
from app.models.schema import (
    Company, StateHub, Warehouse, WarehouseType, WarehouseStatus, WarehouseExternalMapping,
    Product, Inventory, InventoryMovement, DocumentSequence,
    Sale, SaleItem, FCDispatch, FCDispatchItem, DispatchTimeline, FCReturn, FCReturnItem, DamageClaim,
    DeliveryChallan
)
from app.models.accounting_schema import AccountingConfiguration
from app.services.inventory_event_engine import InventoryEventEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), '../scratch/data')

def safe_cleanup(db):
    print("STEP 0 - Safe Cleanup: Deleting ONLY transactional data...")
    try:
        # Delete in order of dependencies
        db.query(DispatchTimeline).delete()
        db.query(FCDispatchItem).delete()
        db.query(FCReturnItem).delete()
        db.query(FCReturn).delete()
        db.query(FCDispatch).delete()
        db.query(DamageClaim).delete()
        db.query(DeliveryChallan).delete()
        db.query(SaleItem).delete()
        db.query(Sale).delete()
        db.query(InventoryMovement).delete()
        db.query(Inventory).delete()
        
        # We don't delete companies, state_hubs, warehouses, products, config here
        # because the CSV import will just UPSERT or SKIP existing.
        
        db.commit()
        print("✔ Safe Cleanup Completed.")
    except Exception as e:
        db.rollback()
        print(f"Cleanup failed: {e}")
        raise

def import_companies(db):
    print("STEP 1 - Companies Setup...")
    try:
        jspl = db.query(Company).filter_by(code="JSPL").first()
        if not jspl:
            jspl = Company(name="JSPL", code="JSPL", is_active=True)
            db.add(jspl)
            db.commit()
        return jspl
    except Exception as e:
        db.rollback()
        raise

def import_state_hubs(db, jspl):
    print("STEP 2 - State Hubs Import...")
    try:
        path = os.path.join(DATA_DIR, "state_hubs.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hub = db.query(StateHub).filter_by(company_id=jspl.id, hub_code=row['state_hub_code']).first()
                if not hub:
                    hub = StateHub(
                        company_id=jspl.id,
                        hub_code=row['state_hub_code'],
                        hub_name=row['state_hub_name'],
                        gstin=row['gstin'] if row['gstin'] else None,
                        address=row['address'],
                        city=row['city'],
                        state=row['state'],
                        state_code=row['state_code'],
                        contact_person=row['contact_person'],
                        phone=row['phone'],
                        email=row['email'],
                        status=row['status']
                    )
                    db.add(hub)
        db.commit()
        print("✔ State Hubs Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_warehouses(db, jspl):
    print("STEP 3 - Warehouses Import...")
    try:
        path = os.path.join(DATA_DIR, "warehouses.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wh = db.query(Warehouse).filter_by(company_id=jspl.id, code=row['warehouse_code']).first()
                if not wh:
                    state_hub = db.query(StateHub).filter_by(company_id=jspl.id, hub_code=row['state_hub_code']).first()
                    wh_type_str = row['warehouse_type']
                    if wh_type_str == 'AMAZON_FC':
                        wh_type_str = 'FULFILLMENT_CENTER'
                    wh = Warehouse(
                        company_id=jspl.id,
                        code=row['warehouse_code'],
                        name=row['warehouse_name'],
                        warehouse_type=getattr(WarehouseType, wh_type_str),
                        hub_id=state_hub.id if state_hub else None,
                        address=row['address'],
                        status=getattr(WarehouseStatus, row['status'])
                    )
                    db.add(wh)
        db.commit()
        print("✔ Warehouses Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_amazon_mapping(db, jspl):
    print("STEP 4 - Amazon Mapping Import...")
    try:
        path = os.path.join(DATA_DIR, "amazon_mapping.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wh = db.query(Warehouse).filter_by(company_id=jspl.id, code=row['warehouse_code']).first()
                if wh:
                    mapping = db.query(WarehouseExternalMapping).filter_by(warehouse_id=wh.id, marketplace=row['marketplace']).first()
                    if not mapping:
                        mapping = WarehouseExternalMapping(
                            warehouse_id=wh.id,
                            marketplace=row['marketplace'],
                            external_code=row['external_fc_code']
                        )
                        db.add(mapping)
        db.commit()
        print("✔ Amazon Mappings Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_products(db, jspl):
    print("STEP 5 - Products Import...")
    try:
        path = os.path.join(DATA_DIR, "products.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku'].strip().upper()
                prod = db.query(Product).filter_by(sku=sku).first()
                if not prod:
                    prod = Product(
                        company_id=jspl.id,
                        sku=sku,
                        name=row['product_name'],
                        hsn_code=row['hsn_code'],
                        default_gst_rate=float(row['gst_rate']),
                        unit=row['unit'],
                        status=row['status']
                    )
                    db.add(prod)
        db.commit()
        print("✔ Products Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_opening_inventory(db, jspl):
    print("STEP 6 - Opening Inventory Import...")
    try:
        path = os.path.join(DATA_DIR, "opening_inventory.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku'].strip().upper()
                qty = int(row['quantity'])
                wh_code = row['warehouse_code']
                
                wh = db.query(Warehouse).filter_by(company_id=jspl.id, code=wh_code).first()
                prod = db.query(Product).filter_by(sku=sku).first()
                
                if wh and prod and qty >= 0:
                    InventoryEventEngine.process_event(
                        db=db,
                        company_id=jspl.id,
                        product_sku=sku,
                        warehouse_id=wh.id,
                        quantity=qty,
                        event_type="OPENING_BALANCE",
                        source="MIGRATION",
                        reference_id=f"OB_{wh_code}_{sku}"
                    )
        db.commit()
        print("✔ Opening Inventory Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_document_sequences(db, jspl):
    print("STEP 7 - Document Sequences Import...")
    try:
        path = os.path.join(DATA_DIR, "document_sequences.csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq = db.query(DocumentSequence).filter_by(
                    company_id=jspl.id, 
                    document_type=row['document_type'],
                    fiscal_year=row['fiscal_year']
                ).first()
                if not seq:
                    seq = DocumentSequence(
                        company_id=jspl.id,
                        document_type=row['document_type'],
                        fiscal_year=row['fiscal_year'],
                        prefix=row['prefix'],
                        last_number=int(row['last_number'])
                    )
                    db.add(seq)
        db.commit()
        print("✔ Document Sequences Imported.")
    except Exception as e:
        db.rollback()
        raise

def import_voucher_mappings(db, jspl):
    print("STEP 8 - Voucher Mappings Import...")
    try:
        path = os.path.join(DATA_DIR, "voucher_mappings.json")
        with open(path, "r", encoding="utf-8") as f:
            mappings = json.load(f)
            
        config = db.query(AccountingConfiguration).filter_by(company_id=jspl.id).first()
        if not config:
            config = AccountingConfiguration(
                company_id=jspl.id,
                tally_company_name="JSPL Tally",
                voucher_type_mappings=mappings
            )
            db.add(config)
        else:
            config.voucher_type_mappings = mappings
        db.commit()
        print("✔ Voucher Mappings Imported.")
    except Exception as e:
        db.rollback()
        raise

def run_import():
    db = SessionLocal()
    try:
        safe_cleanup(db)
        jspl = import_companies(db)
        import_state_hubs(db, jspl)
        import_warehouses(db, jspl)
        import_amazon_mapping(db, jspl)
        import_products(db, jspl)
        import_opening_inventory(db, jspl)
        import_document_sequences(db, jspl)
        import_voucher_mappings(db, jspl)
        
        print("🎉 PRODUCTION DATA IMPORT COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"❌ IMPORT FAILED: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_import()
