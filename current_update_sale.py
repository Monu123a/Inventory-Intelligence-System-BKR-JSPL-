def update_sale(
    sale_id: int,
    payload: PosCheckoutRequest,
    company_id: int = Depends(get_bkr_company_id),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.services.inventory_event_engine import InventoryEventEngine
    
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.company_id == company_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    if sale.status == 'Cancelled':
        raise HTTPException(status_code=400, detail="Cannot edit a cancelled sale")
        
    # Validation: Ensure no returns exist
    active_returns = db.query(SalesReturn).filter(SalesReturn.sale_id == sale.id, SalesReturn.status != 'Cancelled').all()
    if active_returns:
        raise HTTPException(status_code=400, detail="Cannot edit a sale that has active sales returns. Please cancel the returns first.")

    # 1. Header Updates
    sale.customer_name = payload.customer_name
    sale.customer_gstin = payload.customer_gstin
    sale.customer_address = payload.customer_address
    sale.customer_state = payload.customer_state
    sale.customer_state_code = payload.customer_state_code
    sale.customer_phone = payload.customer_phone
    sale.customer_mobile = payload.customer_mobile
    sale.customer_email = payload.customer_email
    sale.place_of_supply = payload.place_of_supply
    sale.shipping_name = payload.shipping_name
    sale.shipping_address = payload.shipping_address
    sale.shipping_state = payload.shipping_state
    sale.shipping_state_code = payload.shipping_state_code
    sale.shipping_gstin = payload.shipping_gstin
    sale.invoice_type = payload.invoice_type
    
    if payload.custom_invoice_date:
        sale.created_at = payload.custom_invoice_date
        sale.sale_date = payload.custom_invoice_date
        
    sale.vehicle_number = payload.vehicle_number
    sale.lr_rr_number = payload.lr_rr_number
    sale.terms_of_delivery = payload.terms_of_delivery
    sale.delivery_note = payload.delivery_note
    sale.delivery_note_date = payload.delivery_note_date
    sale.dispatch_document_number = payload.dispatch_document_number
    sale.dispatch_through = payload.dispatch_through
    
    sale.total_taxable_amount = payload.total_taxable_amount
    sale.total_tax = payload.total_tax
    sale.grand_total = payload.grand_total
    
    # Reset Tally sync
    if sale.tally_sync_status in ['COMPLETED', 'FAILED', 'PENDING']:
        sale.tally_sync_status = 'PENDING'
        
    # 2. Resolve default warehouse for delta tracking
    if payload.origin_warehouse_id:
        default_warehouse = db.query(Warehouse).filter(Warehouse.id == payload.origin_warehouse_id).first()
    else:
        default_warehouse = _resolve_default_warehouse(db, company_id)
        
    if not default_warehouse:
        raise HTTPException(status_code=400, detail="Warehouse not found for delta processing")

    # 3. Item Delta Calculation
    old_items = {item.id: item for item in sale.items}
    new_items_payload = payload.items or []
    
    # Process updates and additions
    for req_item in new_items_payload:
        product = db.query(Product).filter(Product.id == req_item.product_id).first()
        if not product:
            continue
            
        # Is it an existing item that came back from the UI? 
        # (Assuming the UI passes back the sale_item.id if it existed, we need a way to match them. 
        # If UI doesn't have sale_item.id, we map by SKU)
        existing_item = next((oi for oi in old_items.values() if oi.sku == (req_item.sku or product.sku)), None)
        
        delta_qty = req_item.quantity
        if existing_item:
            delta_qty = req_item.quantity - existing_item.quantity
            
            # Update existing row
            existing_item.quantity = req_item.quantity
            existing_item.selling_price = req_item.selling_price
            existing_item.gst_rate = req_item.gst_rate
            existing_item.taxable_amount = req_item.taxable_amount
            existing_item.cgst = req_item.cgst
            existing_item.sgst = req_item.sgst
            existing_item.igst = req_item.igst
            existing_item.line_total = req_item.line_total
            existing_item.product_name = req_item.product_name or product.name
            existing_item.hsn_sac = req_item.hsn_sac or product.hsn
            existing_item.unit = product.unit
            existing_item.discount = req_item.discount or 0.0
            
            del old_items[existing_item.id] # mark as processed
        else:
            # Create new row
            new_sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                sku=product.sku,
                quantity=req_item.quantity,
                selling_price=req_item.selling_price,
                gst_rate=req_item.gst_rate,
                taxable_amount=req_item.taxable_amount,
                cgst=req_item.cgst,
                sgst=req_item.sgst,
                igst=req_item.igst,
                line_total=req_item.line_total,
                product_name=req_item.product_name or product.name,
                hsn_sac=req_item.hsn_sac or product.hsn,
                unit=product.unit,
                discount=req_item.discount or 0.0
            )
            db.add(new_sale_item)
            
        # Apply Inventory Delta
        if delta_qty != 0 and not payload.skip_inventory_update:
            event_type = "SALE" if delta_qty > 0 else "ADD"
            source = "OFFLINE_POS" if delta_qty > 0 else "INVOICE_EDIT"
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=product.sku,
                warehouse_id=default_warehouse.id,
                quantity=abs(delta_qty),
                event_type=event_type,
                source=source,
                reference_id=sale.bill_number,
                metadata_payload={"sale_id": sale.id, "edit_delta": delta_qty},
                
            )
            
    # Process removals (anything left in old_items was deleted from the UI)
    for oi in old_items.values():
        if not payload.skip_inventory_update:
            InventoryEventEngine.process_event(
                db=db,
                company_id=company_id,
                product_sku=oi.sku,
                warehouse_id=default_warehouse.id,
                quantity=oi.quantity,
                event_type="ADD",
                source="INVOICE_EDIT",
                reference_id=sale.bill_number,
                metadata_payload={"sale_id": sale.id, "edit_delta": -oi.quantity},
                
            )
        db.delete(oi)

    db.commit()
