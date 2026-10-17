#!/usr/bin/env python3
"""
Bulk Product Import Script for Inventory Intelligence System (BKR & JSPL)
==========================================================================
Adheres strictly to the guidelines in AGENTS.md:
- Raw psycopg2 and psycopg2.extras.execute_values for bulk database updates.
- Fast, locked-connection-free, single-query execution.
- Reads centralized DATABASE_URL from .env or centralized fallback.
- Flexible header alias matching for .xlsx and .csv.
- Deduce GST calculations: Price_excl_GST = Price_incl_GST / (1 + (GST % / 100)).
- SKU pattern extraction: \\b[A-Za-z]{2}\\d{4}[0-9A-Za-z\\-]*\\b
- Strict SKU variant isolation (e.g. LG0831-1 is distinct from LG0831).
- Dry-run capability (--dry-run) to preview changes before execution.
- Optional initial stock initialization into company Central Warehouse.
"""

import os
import sys
import re
import argparse
import math
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# 1. Load Environment & Database Connection
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
CENTRAL_DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
DATABASE_URL = os.environ.get("DATABASE_URL") or CENTRAL_DATABASE_URL

# Regex for standard SKU pattern extraction
SKU_REGEX = re.compile(r'\b[A-Za-z]{2}\d{4}[0-9A-Za-z\-]*\b')

# Standard Column Aliases Mapping
COLUMN_ALIASES = {
    "sku": ["sku", "productsku", "itemsku", "itemcode", "code", "partnumber", "model", "modelno"],
    "name": ["productname", "name", "itemname", "title", "description", "itemdescription", "particulars"],
    "category": ["category", "productcategory", "itemcategory", "group", "subcategory"],
    "brand": ["brand", "make", "manufacturer", "company"],
    "item_rate": ["rateexclgst", "itemrate", "rate", "sellingprice", "price", "unitprice", "basicrate"],
    "price_incl_gst": ["priceinclgst", "mrp", "grossprice", "grossrate", "inclgstprice", "pricewithgst"],
    "default_gst_rate": ["gstrate", "gst%", "taxrate", "tax%", "gst"],
    "hsn": ["hsn", "hsncode", "hsnsac", "sac"],
    "unit": ["unit", "uom", "unitofmeasure", "measurementunit"],
    "barcode": ["barcode", "ean", "upc"],
    "min_stock_level": ["minstocklevel", "minstock", "minimumstock", "safetystocklevel"],
    "reorder_level": ["reorderlevel", "reorderpoint", "rop"],
    "safety_stock": ["safetystock", "bufferstock"],
    "status": ["status", "productstatus", "activeinactive"],
    "initial_stock": ["initialstock", "openingstock", "quantity", "qty", "stock"]
}

def normalize_key(name: str) -> str:
    """Normalize column header: lowercase and strip spaces/punctuation."""
    if not isinstance(name, str):
        return ""
    return re.sub(r'[^a-zA-Z0-9%]', '', name.strip().lower())

def clean_str(val: Any) -> Optional[str]:
    """Clean string value, stripping whitespace and returning None for empty/nan."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ["nan", "none", "null"] else None

def clean_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if val is None or pd.isna(val):
        return default
    try:
        f = float(str(val).replace(",", "").strip())
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return default

def clean_int(val: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if val is None or pd.isna(val):
        return default
    try:
        f = float(str(val).replace(",", "").strip())
        return default if math.isnan(f) or math.isinf(f) else int(f)
    except (ValueError, TypeError):
        return default

def map_dataframe_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Map raw dataframe columns to canonical field names using aliases."""
    mapped = {}
    normalized_cols = {normalize_key(col): col for col in df.columns}
    
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_alias = normalize_key(alias)
            if norm_alias in normalized_cols:
                mapped[field] = normalized_cols[norm_alias]
                break
    return mapped

def extract_sku(raw_sku: Optional[str], raw_name: Optional[str]) -> Optional[str]:
    """
    Extract and validate SKU per AGENTS.md rules.
    1. If explicit SKU exists, strip and return it.
    2. Fall back to regex pattern match in product name.
    """
    if raw_sku:
        s = raw_sku.strip()
        if s:
            return s
    if raw_name:
        match = SKU_REGEX.search(raw_name)
        if match:
            return match.group(0).strip()
    return None

def resolve_company(conn, company_arg: Optional[str], company_id_arg: Optional[int]) -> Tuple[int, str, int]:
    """
    Resolve company ID, name, and central warehouse ID.
    Returns: (company_id, company_code, central_warehouse_id)
    """
    with conn.cursor() as cur:
        if company_id_arg:
            cur.execute("SELECT id, code, name FROM companies WHERE id = %s", (company_id_arg,))
        elif company_arg:
            cur.execute("SELECT id, code, name FROM companies WHERE UPPER(code) = UPPER(%s) OR UPPER(name) = UPPER(%s)", (company_arg, company_arg))
        else:
            cur.execute("SELECT id, code, name FROM companies WHERE UPPER(code) = 'BKR' OR UPPER(name) LIKE '%BKR%' LIMIT 1")
            
        comp = cur.fetchone()
        if not comp:
            raise ValueError(f"Company '{company_arg or company_id_arg}' not found in database.")
            
        c_id, c_code, c_name = comp
        
        # Resolve central warehouse
        cur.execute("""
            SELECT id FROM warehouses 
            WHERE company_id = %s AND (warehouse_type = 'CENTRAL' OR UPPER(name) LIKE '%%CENTRAL%%')
            ORDER BY (CASE WHEN warehouse_type = 'CENTRAL' THEN 0 ELSE 1 END), id DESC LIMIT 1;
        """, (c_id,))
        wh = cur.fetchone()
        central_wh_id = wh[0] if wh else None
        
        return c_id, c_code, central_wh_id

def parse_product_file(file_path: str, sheet_name: Any = 0) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse Excel or CSV file into validated product dictionaries.
    Returns: (valid_products, invalid_rows)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    elif ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please provide .xlsx, .xls, or .csv")
        
    mapped_cols = map_dataframe_columns(df)
    
    valid_products = []
    invalid_rows = []
    seen_skus = set()
    
    for idx, row in df.iterrows():
        excel_row_num = idx + 2 # Accounting for 0-index + header row
        
        raw_sku = clean_str(row.get(mapped_cols.get("sku"))) if "sku" in mapped_cols else None
        raw_name = clean_str(row.get(mapped_cols.get("name"))) if "name" in mapped_cols else None
        
        sku = extract_sku(raw_sku, raw_name)
        if not sku:
            invalid_rows.append({
                "row": excel_row_num,
                "error": "Missing valid SKU (Could not extract from SKU column or Product Name)",
                "data": dict(row)
            })
            continue
            
        if not raw_name:
            invalid_rows.append({
                "row": excel_row_num,
                "sku": sku,
                "error": "Missing required Product Name",
                "data": dict(row)
            })
            continue
            
        if sku in seen_skus:
            invalid_rows.append({
                "row": excel_row_num,
                "sku": sku,
                "error": f"Duplicate SKU '{sku}' within the same import file",
                "data": dict(row)
            })
            continue
            
        seen_skus.add(sku)
        
        # Parse fields
        category = clean_str(row.get(mapped_cols.get("category"))) if "category" in mapped_cols else ""
        brand = clean_str(row.get(mapped_cols.get("brand"))) if "brand" in mapped_cols else ""
        hsn = clean_str(row.get(mapped_cols.get("hsn"))) if "hsn" in mapped_cols else ""
        barcode = clean_str(row.get(mapped_cols.get("barcode"))) if "barcode" in mapped_cols else ""
        unit = clean_str(row.get(mapped_cols.get("unit"))) or "PCS"
        status = clean_str(row.get(mapped_cols.get("status"))) or "Active"
        
        min_stock = clean_int(row.get(mapped_cols.get("min_stock_level")), 0) if "min_stock_level" in mapped_cols else 0
        reorder_level = clean_int(row.get(mapped_cols.get("reorder_level")), 0) if "reorder_level" in mapped_cols else 0
        safety_stock = clean_int(row.get(mapped_cols.get("safety_stock")), 0) if "safety_stock" in mapped_cols else 0
        initial_stock = clean_int(row.get(mapped_cols.get("initial_stock")), 0) if "initial_stock" in mapped_cols else 0
        
        # GST & Rate calculations (Rule 5: Deduce GST Price_excl_GST = Price_incl_GST / (1 + (GST % / 100)))
        raw_gst = clean_float(row.get(mapped_cols.get("default_gst_rate")), 18.0) if "default_gst_rate" in mapped_cols else 18.0
        gst_rate = round(raw_gst, 2)
        
        rate_excl = clean_float(row.get(mapped_cols.get("item_rate")), 0.0) if "item_rate" in mapped_cols else 0.0
        price_incl = clean_float(row.get(mapped_cols.get("price_incl_gst")), 0.0) if "price_incl_gst" in mapped_cols else 0.0
        
        if rate_excl > 0:
            item_rate = round(rate_excl, 2)
        elif price_incl > 0:
            item_rate = round(price_incl / (1.0 + (gst_rate / 100.0)), 2)
        else:
            item_rate = 0.0
            
        valid_products.append({
            "sku": sku,
            "name": raw_name,
            "category": category or "",
            "brand": brand or "",
            "item_rate": item_rate,
            "default_gst_rate": gst_rate,
            "hsn": hsn or "",
            "hsn_code": hsn or "",
            "barcode": barcode or "",
            "unit": unit.upper(),
            "min_stock_level": min_stock,
            "reorder_level": reorder_level,
            "safety_stock": safety_stock,
            "preferred_transfer_qty": 1,
            "status": "Active" if status.lower() in ["active", "1", "true"] else "Inactive",
            "initial_stock": initial_stock
        })
        
    return valid_products, invalid_rows

def run_bulk_import(
    file_path: str,
    company: Optional[str] = "BKR",
    company_id: Optional[int] = None,
    dry_run: bool = False,
    update_existing: bool = False,
    init_stock: bool = True,
    sheet_name: Any = 0
) -> Dict[str, Any]:
    """
    Execute bulk import following all user guidelines and database rules.
    """
    print("=" * 70)
    print("📦 INVENTORY INTELLIGENCE - BULK PRODUCT IMPORT")
    print("=" * 70)
    print(f"File: {file_path}")
    print(f"Mode: {'DRY RUN (Preview Only - No DB changes)' if dry_run else 'LIVE COMMIT'}")
    print(f"Update Existing: {'YES' if update_existing else 'NO (Skip existing)'}")
    print(f"Initialize Stock: {'YES' if init_stock else 'NO'}")
    print("-" * 70)
    
    # 1. Connect to Database
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    
    try:
        # Resolve company
        c_id, c_code, central_wh_id = resolve_company(conn, company, company_id)
        print(f"Target Company: {c_code} (ID: {c_id})")
        print(f"Central Warehouse: ID {central_wh_id or 'None'}")
        
        # 2. Parse file
        valid_products, invalid_rows = parse_product_file(file_path, sheet_name=sheet_name)
        print(f"Total Rows Parsed: {len(valid_products) + len(invalid_rows)}")
        print(f"Valid Product Rows: {len(valid_products)}")
        print(f"Invalid Rows / Conflicts: {len(invalid_rows)}")
        
        if invalid_rows:
            print("\n⚠️  INVALID ROWS DETECTED:")
            for inv in invalid_rows[:10]: # Print first 10
                print(f"  • Row {inv['row']}: {inv['error']} (SKU: {inv.get('sku', 'N/A')})")
            if len(invalid_rows) > 10:
                print(f"  ... and {len(invalid_rows) - 10} more.")
                
        if not valid_products:
            print("\n❌ No valid products to import. Aborting.")
            return {"status": "error", "message": "No valid products found"}
            
        # 3. Categorize into New vs Existing SKUs
        with conn.cursor() as cur:
            cur.execute("SELECT sku FROM products WHERE company_id = %s;", (c_id,))
            existing_skus_in_db = set(r[0] for r in cur.fetchall())
            
        new_products = [p for p in valid_products if p["sku"] not in existing_skus_in_db]
        existing_products = [p for p in valid_products if p["sku"] in existing_skus_in_db]
        
        print(f"\n📊 PRODUCT BREAKDOWN:")
        print(f"  • New SKUs to Create: {len(new_products)}")
        print(f"  • Existing SKUs in DB: {len(existing_products)} ({'Will UPDATE' if update_existing else 'Will SKIP'})")
        
        if new_products:
            print("\n✨ Sample New Products to Create:")
            for p in new_products[:5]:
                print(f"  + [{p['sku']}] {p['name']} | Rate: ₹{p['item_rate']} (GST {p['default_gst_rate']}%) | HSN: {p['hsn']} | Init Stock: {p['initial_stock']}")
            if len(new_products) > 5:
                print(f"  ... and {len(new_products) - 5} more new products.")
                
        if existing_products:
            print("\n🔄 Sample Existing Products:")
            for p in existing_products[:5]:
                print(f"  = [{p['sku']}] {p['name']} | Rate: ₹{p['item_rate']} | Action: {'UPDATE' if update_existing else 'SKIP'}")
            if len(existing_products) > 5:
                print(f"  ... and {len(existing_products) - 5} more existing products.")
                
        # Dry-run early exit
        if dry_run:
            print("\n🔍 DRY RUN COMPLETED. No changes were committed to the database.")
            conn.rollback()
            return {
                "status": "dry_run_success",
                "total_parsed": len(valid_products) + len(invalid_rows),
                "valid_count": len(valid_products),
                "new_count": len(new_products),
                "existing_count": len(existing_products),
                "invalid_count": len(invalid_rows),
                "new_skus": [p["sku"] for p in new_products],
                "existing_skus": [p["sku"] for p in existing_products]
            }
            
        # 4. Perform Bulk Insert / Update via psycopg2 execute_values
        products_to_process = valid_products if update_existing else new_products
        if not products_to_process:
            print("\nℹ️ No new products to insert. (Existing SKUs skipped).")
            conn.rollback()
            return {"status": "success", "inserted": 0, "updated": 0}
            
        records = [
            (
                c_id,
                p["sku"],
                p["name"],
                p["category"],
                p["brand"],
                p["item_rate"],
                p["min_stock_level"],
                p["reorder_level"],
                p["safety_stock"],
                p["preferred_transfer_qty"],
                p["status"],
                p["hsn"],
                p["hsn_code"],
                p["default_gst_rate"],
                p["barcode"],
                p["unit"]
            )
            for p in products_to_process
        ]
        
        insert_sql = """
        INSERT INTO products (
            company_id, sku, name, category, brand, item_rate,
            min_stock_level, reorder_level, safety_stock, preferred_transfer_qty,
            status, hsn, hsn_code, default_gst_rate, barcode, unit
        ) VALUES %s
        """
        
        if update_existing:
            insert_sql += """
            ON CONFLICT (company_id, sku) DO UPDATE SET
                name = EXCLUDED.name,
                category = COALESCE(NULLIF(EXCLUDED.category, ''), products.category),
                brand = COALESCE(NULLIF(EXCLUDED.brand, ''), products.brand),
                item_rate = CASE WHEN EXCLUDED.item_rate > 0 THEN EXCLUDED.item_rate ELSE products.item_rate END,
                min_stock_level = EXCLUDED.min_stock_level,
                reorder_level = EXCLUDED.reorder_level,
                safety_stock = EXCLUDED.safety_stock,
                status = EXCLUDED.status,
                hsn = COALESCE(NULLIF(EXCLUDED.hsn, ''), products.hsn),
                hsn_code = COALESCE(NULLIF(EXCLUDED.hsn_code, ''), products.hsn_code),
                default_gst_rate = COALESCE(EXCLUDED.default_gst_rate, products.default_gst_rate),
                barcode = COALESCE(NULLIF(EXCLUDED.barcode, ''), products.barcode),
                unit = COALESCE(NULLIF(EXCLUDED.unit, ''), products.unit)
            RETURNING id, sku, (xmax = 0) AS is_inserted;
            """
        else:
            insert_sql += """
            ON CONFLICT (company_id, sku) DO NOTHING
            RETURNING id, sku, TRUE AS is_inserted;
            """
            
        with conn.cursor() as cur:
            results = execute_values(cur, insert_sql, records, fetch=True)
            inserted_count = sum(1 for r in results if r[2])
            updated_count = sum(1 for r in results if not r[2])
            sku_to_id = {r[1]: r[0] for r in results}
            
            # 5. Initialize Initial Stock if requested
            stock_initialized = 0
            if init_stock and central_wh_id:
                stock_records = []
                movement_records = []
                
                for p in products_to_process:
                    init_qty = p.get("initial_stock", 0)
                    prod_id = sku_to_id.get(p["sku"])
                    if init_qty > 0 and prod_id:
                        stock_records.append((c_id, prod_id, central_wh_id, init_qty, 0, init_qty, 1))
                        movement_records.append((
                            c_id, prod_id, central_wh_id, 0, init_qty, init_qty,
                            "Initial Stock Upload", f"INIT-{p['sku']}", "BULK_IMPORT", 1, "{}"
                        ))
                        
                if stock_records:
                    inv_sql = """
                    INSERT INTO inventory (
                        company_id, product_id, warehouse_id, current_qty, reserved_qty, available_qty, version_id
                    ) VALUES %s
                    ON CONFLICT (company_id, product_id, warehouse_id) DO UPDATE SET
                        current_qty = inventory.current_qty + EXCLUDED.current_qty,
                        available_qty = inventory.available_qty + EXCLUDED.available_qty,
                        last_updated = NOW();
                    """
                    execute_values(cur, inv_sql, stock_records)
                    
                    mov_sql = """
                    INSERT INTO inventory_movements (
                        company_id, product_id, warehouse_id, qty_before, qty_changed, qty_after,
                        source, reference_id, operation_id, user_id, metadata_payload
                    ) VALUES %s;
                    """
                    execute_values(cur, mov_sql, movement_records)
                    stock_initialized = len(stock_records)
                    
        # Commit Transaction
        conn.commit()
        print("-" * 70)
        print("✅ BULK IMPORT COMPLETED SUCCESSFULLY!")
        print(f"  • Products Newly Created: {inserted_count}")
        print(f"  • Products Updated: {updated_count}")
        if stock_initialized > 0:
            print(f"  • Initial Stock Records Initialized: {stock_initialized} (Warehouse ID: {central_wh_id})")
        print("=" * 70)
        
        return {
            "status": "success",
            "inserted": inserted_count,
            "updated": updated_count,
            "stock_initialized": stock_initialized
        }
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR OCCURRED: {str(e)}")
        raise e
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Bulk Import Products from Excel (.xlsx) or CSV file.")
    parser.add_argument("file_path", help="Path to the Excel (.xlsx) or CSV file")
    parser.add_argument("-c", "--company", default="BKR", help="Target company code or name (BKR or JSPL, default: BKR)")
    parser.add_argument("--company-id", type=int, help="Target company ID directly")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run preview without modifying database")
    parser.add_argument("--update-existing", action="store_true", help="Update existing products if SKU already exists")
    parser.add_argument("--no-stock", dest="init_stock", action="store_false", help="Do not initialize initial inventory stock")
    parser.add_argument("--sheet", default=0, help="Excel sheet name or 0-indexed number (default: 0)")
    
    args = parser.parse_args()
    run_bulk_import(
        file_path=args.file_path,
        company=args.company,
        company_id=args.company_id,
        dry_run=args.dry_run,
        update_existing=args.update_existing,
        init_stock=args.init_stock,
        sheet_name=args.sheet
    )

if __name__ == "__main__":
    main()
