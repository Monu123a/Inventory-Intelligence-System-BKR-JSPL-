import os
import sys
import argparse
import pandas as pd
import re

# Add the backend directory to sys.path so we can import from app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.models.db import SessionLocal
from app.models.schema import Product, Warehouse, Inventory
from sqlalchemy import func

def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    # Lowercase
    t = title.lower()
    # Remove special chars: ® ™ - ( )
    t = re.sub(r'[®™\-\(\)]', ' ', t)
    # Collapse multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def get_category(normalized_title: str) -> str:
    # Gardening Tools
    gardening_keywords = ['hedge', 'clipper', 'clippers', 'pruner', 'pruners', 
                          'secateur', 'secateurs', 'lopper', 'loppers', 'hose', 
                          'hose reel', 'sprayer', 'spreader', 'water timer', 
                          'garden tool', 'rake', 'shovel', 'trowel', 'weeder']
    for kw in gardening_keywords:
        # Match as whole word or part of title if appropriate. For simplicity, check if keyword is in the string.
        # To avoid partial matches like 'hose' in 'chose', we can use word boundaries.
        if re.search(r'\b' + kw + r'\b', normalized_title):
            return "Gardening Tools"
            
    # Trimmer Line
    trimmer_keywords = ['trimmer line', 'nylon line', 'brush cutter line']
    for kw in trimmer_keywords:
        if kw in normalized_title:
            return "Trimmer Line"
            
    # Adhesives
    adhesive_keywords = ['glue', 'epoxy', 'adhesive']
    for kw in adhesive_keywords:
        if re.search(r'\b' + kw + r'\b', normalized_title):
            return "Adhesives"
            
    # Adhesive & Fasteners
    fastener_keywords = ['velcro', 'hook & loop', 'fastener']
    for kw in fastener_keywords:
        if kw in normalized_title:
            return "Adhesive & Fasteners"
            
    # Literature
    lit_keywords = ['catalogue', 'catalog', 'manual', 'brochure', 'leaflet']
    for kw in lit_keywords:
        if re.search(r'\b' + kw + r'\b', normalized_title):
            return "Literature"
            
    # Accessories
    acc_keywords = ['accessory', 'spare', 'replacement']
    for kw in acc_keywords:
        if re.search(r'\b' + kw + r'\b', normalized_title):
            return "Accessories"

    return "Miscellaneous"

def run_migration(csv_path: str, dry_run: bool):
    print(f"Starting JSPL Enrichment Migration (Dry Run: {dry_run})")
    
    try:
        df = pd.read_csv(csv_path)
        # Ensure Date is parsed correctly if present
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(by='Date', ascending=False)
            
        df = df.drop_duplicates(subset=['MSKU', 'Location'], keep='first')
        print(f"Loaded {len(df)} unique rows from CSV (latest date per location).")
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    db = SessionLocal()
    COMPANY_ID = 1

    stats = {
        'skipped_rows': 0,
        'products_created': 0,
        'products_updated': 0,
        'warehouses_created': 0,
        'inventory_created': 0,
        'inventory_updated': 0,
        'expected_total_qty': 0
    }

    # Caches to avoid hammering the DB for lookups within the same script run
    warehouse_cache = {}  # location -> warehouse.id
    product_cache = {}    # sku -> product.id

    # Preload existing warehouses and products for JSPL
    for w in db.query(Warehouse).filter(Warehouse.company_id == COMPANY_ID).all():
        warehouse_cache[w.code] = w.id
    
    for p in db.query(Product).filter(Product.company_id == COMPANY_ID).all():
        product_cache[p.sku] = p.id

    try:
        for idx, row in df.iterrows():
            msku = row.get('MSKU')
            location = row.get('Location')
            balance = row.get('Ending Warehouse Balance')
            title = row.get('Title')
            brand = row.get('Brand')

            if pd.isna(msku) or not str(msku).strip() or pd.isna(location) or not str(location).strip():
                print(f"Row {idx + 2} skipped: Missing MSKU or Location.")
                stats['skipped_rows'] += 1
                continue

            msku = str(msku).strip()
            location = str(location).strip()
            
            try:
                balance = int(balance) if pd.notna(balance) else 0
            except ValueError:
                balance = 0
            
            stats['expected_total_qty'] += balance

            # 1. Process Warehouse
            if location not in warehouse_cache:
                w = Warehouse(company_id=COMPANY_ID, name=location, code=location, status="Active")
                db.add(w)
                db.flush() # flush to get the ID
                warehouse_cache[location] = w.id
                stats['warehouses_created'] += 1
                
            warehouse_id = warehouse_cache[location]

            # 2. Process Product
            norm_title = normalize_title(str(title) if pd.notna(title) else "")
            category = get_category(norm_title)
            
            if msku not in product_cache:
                p = Product(
                    company_id=COMPANY_ID,
                    sku=msku,
                    name=str(title) if pd.notna(title) else msku,
                    category=category,
                    brand=str(brand) if pd.notna(brand) else None,
                    status="Active"
                )
                db.add(p)
                db.flush()
                product_cache[msku] = p.id
                stats['products_created'] += 1
            else:
                # Update existing product (only brand, category, status)
                p = db.query(Product).filter(Product.id == product_cache[msku]).first()
                if p:
                    p.brand = str(brand) if pd.notna(brand) else p.brand
                    p.category = category
                    p.status = "Active"
                stats['products_updated'] += 1
                db.flush()
                
            product_id = product_cache[msku]

            # 3. Process Inventory (Silent Seed - No Movement Log)
            inv = db.query(Inventory).filter(
                Inventory.company_id == COMPANY_ID,
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).first()

            if inv:
                inv.current_qty = balance
                inv.available_qty = balance
                stats['inventory_updated'] += 1
            else:
                inv = Inventory(
                    company_id=COMPANY_ID,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    current_qty=balance,
                    available_qty=balance
                )
                db.add(inv)
                stats['inventory_created'] += 1
                
        # Dry Run vs Commit
        if dry_run:
            print("\n--- DRY RUN MODE ---")
            db.rollback()
        else:
            db.commit()
            print("\n--- COMMITTED TO DATABASE ---")

        # Report stats
        print(f"Products to create: {stats['products_created']}")
        print(f"Products to update: {stats['products_updated']}")
        print(f"Warehouses to create: {stats['warehouses_created']}")
        print(f"Inventory records to create: {stats['inventory_created']}")
        print(f"Inventory records to update: {stats['inventory_updated']}")
        print(f"Rows skipped: {stats['skipped_rows']}")

        if not dry_run:
            # Final Verification
            actual_sum = db.query(func.sum(Inventory.available_qty)).filter(Inventory.company_id == COMPANY_ID).scalar() or 0
            print(f"\nFinal Verification:")
            print(f"Expected Sum (CSV): {stats['expected_total_qty']}")
            print(f"Actual Sum (DB):  {actual_sum}")
            if actual_sum == stats['expected_total_qty']:
                print("✅ Verification Passed!")
            else:
                print("❌ Verification Failed! Sums do not match.")

    except Exception as e:
        db.rollback()
        print(f"An error occurred during migration. Rolled back transaction. Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSPL Data Enrichment Migration")
    parser.add_argument("--csv", required=True, help="Path to the source CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    args = parser.parse_args()

    run_migration(args.csv, args.dry_run)
