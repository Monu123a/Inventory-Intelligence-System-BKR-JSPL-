import os
import sys
import time
from datetime import datetime

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.db import SessionLocal
from app.models.schema import (
    Company, Warehouse, Product, Inventory, FCDispatch, FCDispatchItem, 
    Sale, SaleItem, ServiceRecord, DamageClaim, StateHub, WarehouseStatus
)
from app.services.fc_dispatch_service import FCDispatchService, FCDispatchBatchRequest, FCDispatchRequestItem
from app.services.inventory_event_engine import InventoryEventEngine
from app.services.sales_return_service import SalesReturnService
from app.services.tally_payload_builder import TallyPayloadBuilder

def run_simulation(db):
    try:
        print("Starting Simulation Test Flow...")
        company = db.query(Company).filter_by(code="JSPL").first()
        
        # Warehouses
        vshb = db.query(Warehouse).filter_by(company_id=company.id, code="VSHB").first()
        hyd_fc = db.query(Warehouse).filter_by(company_id=company.id, code="HYD_FC").first()
        amz_fc = db.query(Warehouse).filter_by(company_id=company.id, code="HYD_AMZ").first()
        bkr_wh = db.query(Warehouse).filter_by(company_id=company.id, code="BKR").first()
        if not bkr_wh:
            # create a bkr warehouse for simulation if it doesn't exist
            bkr_wh = Warehouse(company_id=company.id, name="BKR Hub", code="BKR", status=WarehouseStatus.ACTIVE)
            db.add(bkr_wh)
            db.commit()

        # Product
        sku = db.query(Product).filter_by(company_id=company.id).first()
        assert sku is not None, "No products found for simulation"
        print(f"STEP 1 - Baseline Check (Dynamically picked SKU: {sku.sku})")
        
        # Inject stock to BKR so it can dispatch
        InventoryEventEngine.process_event(db, company.id, sku.sku, bkr_wh.id, 100, "OPENING_BALANCE", "SIM", "BKR_SIM_STOCK")
        db.commit()
        
        # Log Initial Stock
        vshb_inv = db.query(Inventory).filter_by(warehouse_id=vshb.id, product_id=sku.id).first()
        hyd_inv = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        
        vshb_start_qty = vshb_inv.current_qty if vshb_inv else 0
        hyd_start_qty = hyd_inv.current_qty if hyd_inv else 0
        print(f"  VSHB Stock: {vshb_start_qty}")
        print(f"  HYD_FC Stock: {hyd_start_qty}")

        print("STEP 2 - BKR → VSHB (STANDARD)")
        # Dispatch from BKR to VSHB
        bkr_req = FCDispatchBatchRequest(
            warehouse_ids=[vshb.id],
            hub_id=vshb.hub_id,
            dispatch_type="STANDARD",
            source_warehouse_id=bkr_wh.id,
            items=[FCDispatchRequestItem(product_id=sku.id, quantity=10)]
        )
        bkr_dispatch_result = FCDispatchService.create_batch_dispatch(db, company.id, bkr_req, user_id=None)
        db.commit()
        assert len(bkr_dispatch_result) == 1, "BKR Dispatch should pass"
        print("  ✔ BKR → VSHB dispatch passed.")

        vshb_inv_after_recv = db.query(Inventory).filter_by(warehouse_id=vshb.id, product_id=sku.id).first()
        db.refresh(vshb_inv_after_recv)
        print(f"DEBUG: VSHB qty is {vshb_inv_after_recv.current_qty}")
        assert vshb_inv_after_recv.current_qty == vshb_start_qty + 10, "VSHB inventory should have increased"
        print("  ✔ VSHB Inventory increased correctly.")

        print("STEP 3 - VSHB → FC (STANDARD)")
        vshb_req = FCDispatchBatchRequest(
            warehouse_ids=[hyd_fc.id],
            hub_id=hyd_fc.hub_id,
            dispatch_type="STANDARD",
            source_warehouse_id=vshb.id,
            items=[FCDispatchRequestItem(product_id=sku.id, quantity=5)]
        )
        vshb_dispatch_result = FCDispatchService.create_batch_dispatch(db, company.id, vshb_req, user_id=None)
        db.commit()
        assert len(vshb_dispatch_result) == 1, "VSHB -> FC Dispatch should pass"
        
        vshb_inv_after_disp = db.query(Inventory).filter_by(warehouse_id=vshb.id, product_id=sku.id).first()
        assert vshb_inv_after_disp.current_qty == vshb_start_qty + 10 - 5, "VSHB inventory should have decreased"
        print("  ✔ VSHB → FC standard dispatch passed and inventory deducted.")

        print("STEP 4 - EMERGENCY (VALID) VSHB → FC")
        emerg_valid_req = FCDispatchBatchRequest(
            warehouse_ids=[hyd_fc.id],
            hub_id=hyd_fc.hub_id,
            dispatch_type="EMERGENCY",
            source_warehouse_id=vshb.id,
            items=[FCDispatchRequestItem(product_id=sku.id, quantity=1)]
        )
        emerg_valid_result = FCDispatchService.create_batch_dispatch(db, company.id, emerg_valid_req, user_id=None)
        db.commit()
        assert len(emerg_valid_result) == 1, "Emergency dispatch from VSHB should pass"
        print("  ✔ VSHB → FC emergency dispatch passed.")

        print("STEP 5 - EMERGENCY (INVALID) BKR → FC")
        try:
            emerg_invalid_req = FCDispatchBatchRequest(
                warehouse_ids=[hyd_fc.id],
                hub_id=hyd_fc.hub_id,
                dispatch_type="EMERGENCY",
                source_warehouse_id=bkr_wh.id,
                items=[FCDispatchRequestItem(product_id=sku.id, quantity=1)]
            )
            FCDispatchService.create_batch_dispatch(db, company.id, emerg_invalid_req, user_id=None)
            assert False, "Should have failed!"
        except Exception as e:
            assert "EMERGENCY dispatches must originate from VSHB" in str(e)
            print("  ✔ BKR → FC emergency dispatch correctly blocked.")

        print("STEP 6 - Amazon Blocking Test")
        try:
            amz_req = FCDispatchBatchRequest(
                warehouse_ids=[amz_fc.id],
                hub_id=amz_fc.hub_id,
                dispatch_type="STANDARD",
                source_warehouse_id=vshb.id,
                items=[FCDispatchRequestItem(product_id=sku.id, quantity=1)]
            )
            FCDispatchService.create_batch_dispatch(db, company.id, amz_req, user_id=None)
            assert False, "Should have failed!"
        except Exception as e:
            assert "Amazon FCs are not permitted for internal distribution" in str(e)
            print("  ✔ Amazon FC dispatch correctly blocked.")

        print("STEP 7 - Sale Simulation from FC")
        hyd_inv_before_sale = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        hyd_start_qty_sale = hyd_inv_before_sale.current_qty
        print(f"DEBUG: HYD FC qty before sale is {hyd_start_qty_sale}")
        
        # Create a mock Sale
        sale = Sale(
            company_id=company.id,
            bill_number=f"INV/SIM/{int(time.time())}",
            sale_date=datetime.now(),
            customer_name="Test Customer"
        )
        db.add(sale)
        db.flush()
        
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=sku.id,
            sku=sku.sku,
            quantity=2,
            selling_price=10.0,
            taxable_amount=20.0
        )
        db.add(sale_item)
        db.flush()
        
        InventoryEventEngine.process_event(db, company.id, sku.sku, hyd_fc.id, 2, "SALE", "POS_SALE", sale.bill_number)
        db.commit()
        
        hyd_inv_after_sale = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        db.refresh(hyd_inv_after_sale)
        hyd_after_sale_qty = hyd_inv_after_sale.current_qty
        assert hyd_after_sale_qty == hyd_start_qty_sale - 2, "Sale should deduct inventory"
        print("  ✔ Sale simulation passed.")

        print("STEP 8 - Return Flow")
        ret_req_dict = {
            "sale_id": sale.id,
            "warehouse_id": hyd_fc.id,
            "items": [
                {
                    "sale_item_id": sale_item.id,
                    "returned_quantity": 1, 
                    "return_reason": "Customer didn't like it"
                }
            ]
        }
        draft_return = SalesReturnService.create_draft(db, company.id, ret_req_dict, user_id=None)
        db.commit()
        SalesReturnService.complete_return(db, company.id, draft_return.id, user_id=None)
        db.commit()
        
        hyd_inv_after_ret = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        db.refresh(hyd_inv_after_ret)
        hyd_after_ret_qty = hyd_inv_after_ret.current_qty
        assert hyd_after_ret_qty == hyd_after_sale_qty + 1, "Return should add inventory"
        print("  ✔ Return flow passed.")

        print("STEP 9 - Damage Entry")
        damage = DamageClaim(
            company_id=company.id,
            warehouse_id=hyd_fc.id,
            product_id=sku.id,
            claim_number=f"DAM/SIM/{int(time.time())}",
            quantity=1,
            claim_status="Approved"
        )
        db.add(damage)
        db.flush()
        InventoryEventEngine.process_event(db, company.id, sku.sku, hyd_fc.id, 1, "DAMAGE_WRITE_OFF", "DAMAGE_CLAIM", damage.claim_number)
        db.commit()
        
        hyd_inv_after_dam = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        db.refresh(hyd_inv_after_dam)
        hyd_after_dam_qty = hyd_inv_after_dam.current_qty
        assert hyd_after_dam_qty == hyd_after_ret_qty - 1, "Damage should deduct inventory"
        print("  ✔ Damage entry passed.")

        print("STEP 10 - XML Export Generation")
        xml_payload = TallyPayloadBuilder.build_xml(sale)
        
        assert xml_payload is not None, "XML should be generated"
        assert "<Invoice" in xml_payload, "XML should contain Invoice tag"
        print("  ✔ XML Export passed")

        print("STEP 11 - Validate Reports / DB State")
        # Ensure all models reflect the right states
        assert hyd_after_dam_qty == hyd_start_qty + 6 - 2 + 1 - 1
        print("  ✔ DB State matches expected values.")

        print("STEP 12 - Final Inventory Reconciliation")
        # Opening: vshb_start_qty + hyd_start_qty
        # Inward (BKR to VSHB): +10
        # Sales: -2
        # Returns: +1
        # Damage: -1
        # Internal transfer (-6 from VSHB, +6 to HYD) nets to 0 overall
        total_opening = vshb_start_qty + hyd_start_qty
        total_inward = 10
        total_sales = 2
        total_returns = 1
        total_damage = 1
        
        expected_closing = total_opening + total_inward - total_sales + total_returns - total_damage
        
        vshb_inv = db.query(Inventory).filter_by(warehouse_id=vshb.id, product_id=sku.id).first()
        db.refresh(vshb_inv)
        hyd_inv = db.query(Inventory).filter_by(warehouse_id=hyd_fc.id, product_id=sku.id).first()
        db.refresh(hyd_inv)
        vshb_final = vshb_inv.current_qty
        hyd_final = hyd_inv.current_qty
        actual_closing = vshb_final + hyd_final
        
        assert actual_closing == expected_closing, f"Reconciliation failed! Expected {expected_closing}, got {actual_closing}"
        print(f"  ✔ Reconciliation Passed! (Total Closing: {actual_closing})")
        
        print("\n🏆 FULL SIMULATION SUCCESSFUL!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ SIMULATION FAILED: {str(e)}")
        raise

if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_simulation(db)
    finally:
        db.close()
