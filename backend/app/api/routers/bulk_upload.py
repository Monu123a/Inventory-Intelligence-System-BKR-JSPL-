import os
import shutil
from datetime import datetime
import pandas as pd
import io
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.schema import Product
from app.api.dependencies import get_current_company_id, get_current_user

router = APIRouter(prefix="/bulk-upload", tags=["Bulk Upload"])

@router.post("/tally-bill-preview")
async def tally_bill_preview(
    request: Request,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id)
):
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            raise Exception("File is missing from form data")
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
                
                import math
                try:
                    qty = int(float(qty))
                    rate = float(rate)
                    gst = float(gst)
                    
                    if math.isnan(qty): qty = 0
                    if math.isnan(rate): rate = 0.0
                    if math.isnan(gst): gst = 0.0
                except:
                    continue
                    
                if qty <= 0:
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
from app.services.inventory_event_engine import InventoryEventEngine


import traceback
from functools import wraps
from fastapi import HTTPException

def catch_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Confirm Error: {str(e)}")
    return wrapper

@router.post("/tally-bill-confirm")
@catch_exceptions
async def tally_bill_confirm(
    request: Request,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    try:
        form = await request.form()
        file = form.get("file")
        warehouse_id_str = form.get("warehouse_id")
        items = form.get("items")
        if not file or not warehouse_id_str or not items:
            raise HTTPException(status_code=400, detail="Missing required form fields")
        warehouse_id = int(warehouse_id_str)

        parsed_items = json.loads(items)
    except:
        raise HTTPException(status_code=400, detail="Invalid items payload")
        
    if not parsed_items:
        raise HTTPException(status_code=400, detail="No items to update")


    # Save the file permanently
    os.makedirs("uploads/tally_bills", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%md_%H%M%S")
    safe_filename = f"{timestamp}_{uuid.uuid4().hex[:6]}_{file.filename}"
    file_path = os.path.join("uploads", "tally_bills", safe_filename)
    
    content_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(content_bytes)

    file_reference = f"Tally Upload: {safe_filename}"


    operator_id = current_user.id

    for i, item in enumerate(parsed_items):
        product_sku = item.get("matched_sku")
        qty = item.get("quantity", 0)
        
        if not product_sku or qty <= 0:
            continue
            
        InventoryEventEngine.process_event(
            db=db,
            company_id=company_id,
            product_sku=product_sku,
            warehouse_id=warehouse_id,
            quantity=qty,
            event_type="ADD",
            source="Tally Upload",
            reference_id=file_reference,
            user_id=operator_id,
            metadata_payload={"rate": item.get('rate'), "gst": item.get('gst_rate'), "line_id": str(item.get('sl_no') or i)},
            allow_negative_stock=False
        )
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Duplicate Upload Detected: This Tally bill has already been uploaded.")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {"status": "success", "message": "Inventory updated successfully"}

from fastapi.responses import FileResponse

@router.get("/download-tally-bill/{filename}")
def download_tally_bill(filename: str, current_user: User = Depends(get_current_user)):
    file_path = os.path.join("uploads", "tally_bills", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)
