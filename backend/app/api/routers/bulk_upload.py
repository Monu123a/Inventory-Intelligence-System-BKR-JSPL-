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
        sl = str(df.iloc[idx, 0]).strip()
        if pd.isna(df.iloc[idx, 0]) or sl == "" or sl.lower() == "nan" or "total" in sl.lower():
            if pd.isna(df.iloc[idx, 9]):
                continue

        qty = df.iloc[idx, 9]
        if pd.isna(qty):
            continue
            
        desc = str(df.iloc[idx, 1]).strip()
        rate = df.iloc[idx, 10]
        gst = df.iloc[idx, 8]
        
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

        hsn = str(df.iloc[idx, 7]).replace('.0','') if not pd.isna(df.iloc[idx, 7]) else ""

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

    return {"items": items}

import json
from fastapi import Form
from app.models.schema import Inventory, InventoryTransaction, User

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

    for item in parsed_items:
        product_id = item.get("product_id")
        qty = item.get("quantity", 0)
        
        if not product_id or qty <= 0:
            continue
            
        # Get or create inventory record
        inv = db.query(Inventory).filter(
            Inventory.warehouse_id == warehouse_id,
            Inventory.product_id == product_id
        ).first()
        
        if not inv:
            inv = Inventory(
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=qty
            )
            db.add(inv)
        else:
            inv.quantity += qty
            
        db.flush()
        
        # Create transaction
        txn = InventoryTransaction(
            inventory_id=inv.id,
            transaction_type="IN",
            quantity=qty,
            operator_id=operator_id,
            reference_document=file_reference,
            remarks=f"Bulk upload from Tally - Rate: {item.get('rate')} GST: {item.get('gst_rate')}"
        )
        db.add(txn)
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {"status": "success", "message": "Inventory updated successfully"}
