import pandas as pd
import io
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.schema import Product
from app.api.dependencies import get_current_company_id

router = APIRouter(prefix="/bulk-upload", tags=["Bulk Upload"])

@router.post("/tally-bill-preview")
async def tally_bill_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content), sheet_name=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    try:
        products = db.query(Product).filter(Product.company_id == company_id, Product.status == "Active").all()
        sku_map = {p.sku: p for p in products if p.sku}

        start_idx = -1
        for idx, row in df.iterrows():
            val = str(row.iloc[0]).strip().lower()
            if val == "1" or val == "sl" or val == "sl no" or val == "sl. no.":
                start_idx = idx
                break

        if start_idx == -1:
            raise HTTPException(status_code=400, detail="Could not identify item rows. Ensure the first column has serial numbers.")

        item_start = -1
        for idx in range(start_idx, len(df)):
            if str(df.iloc[idx, 0]).strip() == "1":
                item_start = idx
                break

        if item_start == -1:
            raise HTTPException(status_code=400, detail="Could not find item '1'.")

        items = []
        
        for idx in range(item_start, len(df)):
            try:
                sl = str(df.iloc[idx, 0]).strip()
                
                # Check for bounds before accessing
                max_col = len(df.columns) - 1
                
                if pd.isna(df.iloc[idx, 0]) or sl == "" or sl.lower() == "nan" or "total" in sl.lower():
                    if max_col < 9 or pd.isna(df.iloc[idx, 9]):
                        continue

                qty = df.iloc[idx, 9] if max_col >= 9 else 0
                if pd.isna(qty):
                    continue
                    
                desc = str(df.iloc[idx, 1]).strip() if max_col >= 1 else ""
                rate = df.iloc[idx, 10] if max_col >= 10 else 0
                gst = df.iloc[idx, 8] if max_col >= 8 else 0
                
                try:
                    qty = int(qty)
                    rate = float(rate)
                    gst = float(gst)
                except:
                    continue

                matched_sku = None
                matched_product = None
                
                for sku, product in sku_map.items():
                    if sku in desc:
                        matched_sku = sku
                        matched_product = product
                        break
                        
                if not matched_sku:
                    match = re.search(r'[a-zA-Z]{2}\d{4}', desc)
                    if match:
                        candidate = match.group(0).upper()
                        if candidate in sku_map:
                            matched_sku = candidate
                            matched_product = sku_map[candidate]

                hsn = ""
                if max_col >= 7 and not pd.isna(df.iloc[idx, 7]):
                    hsn = str(df.iloc[idx, 7]).replace('.0','')

                items.append({
                    "sl_no": sl if sl != "nan" else "",
                    "description": desc,
                    "quantity": qty,
                    "rate": rate,
                    "gst_rate": gst,
                    "matched_sku": matched_sku,
                    "product_id": matched_product.id if matched_product else None,
                    "product_name": matched_product.name if matched_product else None,
                    "hsn_sac": matched_product.hsn if matched_product else hsn
                })
            except Exception as e:
                # If a single row fails, skip it instead of crashing the whole file
                print(f"Error parsing row {idx}: {e}")
                continue

        return {"items": items}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Data parsing error: {str(e)}")

import json
from fastapi import Form
from app.models.schema import Inventory, InventoryMovement, User

@router.post("/tally-bill-confirm")
async def tally_bill_confirm(
    file: UploadFile = File(...),
    warehouse_id: int = Form(...),
    items: str = Form(...),
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    try:
        parsed_items = json.loads(items)
    except:
        raise HTTPException(status_code=400, detail="Invalid items payload")
        
    if not parsed_items:
        raise HTTPException(status_code=400, detail="No items to update")

    # In a real app we'd save the file to S3. Here we just pretend or save locally.
    # We will log the filename in the transaction reference
    file_reference = f"Tally Upload: {file.filename}"

    # Get admin user id for the transaction (mocking for now, or you can inject current user)
    # Using the first active user for this company
    operator = db.query(User).filter(User.company_id == company_id).first()
    operator_id = operator.id if operator else 1

    for i, item in enumerate(parsed_items):
        product_id = item.get("product_id")
        qty = item.get("quantity", 0)
        
        if not product_id or qty <= 0:
            continue
            
        # Get or create inventory record
        inv = db.query(Inventory).filter(
            Inventory.warehouse_id == warehouse_id,
            Inventory.product_id == product_id
        ).first()
        
        qty_before = 0
        if not inv:
            inv = Inventory(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                current_qty=qty,
                available_qty=qty
            )
            db.add(inv)
        else:
            qty_before = inv.current_qty
            inv.current_qty += qty
            inv.available_qty += qty
            
        db.flush()
        
        # Create transaction
        txn = InventoryMovement(
            company_id=company_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            qty_before=qty_before,
            qty_changed=qty,
            qty_after=qty_before + qty,
            source="Tally Upload",
            reference_id=file_reference,
            operation_id=f"tally_{file.filename}_{i}_{product_id}",
            user_id=operator_id,
            metadata_payload={"rate": item.get('rate'), "gst": item.get('gst_rate')}
        )
        db.add(txn)
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Duplicate Upload Detected: This Tally bill has already been uploaded.")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {"status": "success", "message": "Inventory updated successfully"}
