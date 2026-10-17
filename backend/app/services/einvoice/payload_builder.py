"""
E-Invoice INV-01 Payload Builder (Version 1.1)
==============================================
Transforms an ERP Sale record and warehouse/company context into the
official Government of India E-Invoice JSON standard.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.schema import Sale, Warehouse

# Standard 3-character GST Unit Codes
VALID_GST_UOMS = {
    "PCS": "PCS",
    "NOS": "NOS",
    "SET": "SET",
    "KGS": "KGS",
    "KG": "KGS",
    "MTR": "MTR",
    "BOX": "BOX",
    "PKT": "PAC",
    "PAC": "PAC",
    "BAG": "BAG",
    "BTL": "BTL",
    "CAN": "CAN",
    "ROL": "ROL",
    "UNT": "UNT"
}

def clean_pin(val: Any) -> int:
    """Extract 6-digit numeric PIN code."""
    if not val:
        return 160002 # Default fallback
    m = re.search(r'\b\d{6}\b', str(val))
    return int(m.group(0)) if m else 160002

def clean_state_code(val: Any) -> str:
    """Format state code as 2-digit string (e.g., '04', '29')."""
    if not val:
        return "04"
    s = str(val).strip()
    if len(s) == 1:
        return f"0{s}"
    return s[:2]

def clean_str(val: Any, default: str = "", max_len: int = 100) -> str:
    """Clean string, strip whitespace, and limit length."""
    if val is None:
        return default
    s = str(val).strip()
    return s[:max_len] if s else default

def build_einvoice_payload(sale: Sale, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Builds the official INV-01 Version 1.1 JSON payload for the IRP API.
    """
    # 1. Basic Document Details
    doc_no = sale.invoice_number or sale.bill_number
    # GST rules mandate Doc No length <= 16 characters
    if len(doc_no) > 16:
        # If invoice number is longer than 16 chars, take the suffix or sanitized number
        doc_no = doc_no[-16:]

    sale_date = getattr(sale, "sale_date", None) or getattr(sale, "created_at", None) or datetime.utcnow()
    formatted_date = sale_date.strftime("%d/%m/%Y")

    # 2. Seller Details (Resolved from snapshot or dispatch warehouse)
    seller_gstin = clean_str(sale.company_gstin_snapshot, max_len=15).upper()
    seller_name = clean_str(sale.company_name_snapshot, default="B K RAMAN AND CO", max_len=100)
    seller_addr = clean_str(sale.company_address_snapshot, default="Plot No.150, Industrial Area", max_len=100)
    seller_state_code = clean_state_code(sale.company_state_code_snapshot or (seller_gstin[:2] if len(seller_gstin) >= 2 else "04"))
    seller_state_name = clean_str(sale.company_state_snapshot, default="Chandigarh", max_len=50)
    seller_pin = clean_pin(seller_addr)
    seller_phone = clean_str(sale.company_phone_snapshot, max_len=12)
    seller_email = clean_str(sale.company_email_snapshot, max_len=100)

    # 3. Buyer Details
    buyer_gstin = clean_str(sale.customer_gstin, max_len=15).upper()
    buyer_name = clean_str(sale.customer_name, default="Cash Customer", max_len=100)
    buyer_addr = clean_str(sale.customer_address, default="Market", max_len=100)
    buyer_loc = clean_str(sale.customer_state or getattr(sale, "customer_city", "Local"), default="Local", max_len=50)
    buyer_pin = clean_pin(sale.customer_address)
    buyer_state_code = clean_state_code(sale.customer_state_code or (buyer_gstin[:2] if len(buyer_gstin) >= 2 else seller_state_code))
    pos = clean_state_code(sale.place_of_supply or buyer_state_code)

    # 4. Supply Type (B2B by default for GST customers, or SEZWP, EXPWOP, etc.)
    sup_typ = "B2B"

    # 5. Items List
    items_list = []
    tot_ass_val = 0.0
    tot_cgst = 0.0
    tot_sgst = 0.0
    tot_igst = 0.0
    tot_discount = 0.0

    raw_items = sale.items or []
    for idx, item in enumerate(raw_items, start=1):
        hsn = clean_str(item.hsn_sac, default="84672100", max_len=8)
        # Ensure HSN has at least 4 digits
        if len(hsn) < 4:
            hsn = hsn.ljust(4, '0')

        qty = max(1.0, float(item.quantity or 1))
        unit = VALID_GST_UOMS.get(clean_str(item.unit, default="PCS").upper(), "PCS")
        selling_price = float(item.selling_price or 0.0)
        discount = float(item.discount or 0.0)
        tot_discount += discount

        tot_amt = round(qty * selling_price, 2)
        ass_amt = round(float(item.taxable_amount or (tot_amt - discount)), 2)
        gst_rate = float(item.gst_rate or 0.0)
        
        cgst_amt = round(float(item.cgst or 0.0), 2)
        sgst_amt = round(float(item.sgst or 0.0), 2)
        igst_amt = round(float(item.igst or 0.0), 2)
        tot_item_val = round(ass_amt + cgst_amt + sgst_amt + igst_amt, 2)

        tot_ass_val += ass_amt
        tot_cgst += cgst_amt
        tot_sgst += sgst_amt
        tot_igst += igst_amt

        item_dict = {
            "SlNo": str(idx),
            "PrdDesc": clean_str(item.product_name or item.sku, default=f"Item {idx}", max_len=100),
            "IsServc": "N",
            "HsnCd": hsn,
            "Qty": qty,
            "Unit": unit,
            "UnitPrice": round(selling_price, 2),
            "TotAmt": tot_amt,
            "Discount": round(discount, 2),
            "AssAmt": ass_amt,
            "GstRt": gst_rate,
            "IgstAmt": igst_amt,
            "CgstAmt": cgst_amt,
            "SgstAmt": sgst_amt,
            "CesRt": 0.0,
            "CesAmt": 0.0,
            "CesNonAdvlAmt": 0.0,
            "StateCesRt": 0.0,
            "StateCesAmt": 0.0,
            "StateCesNonAdvlAmt": 0.0,
            "OthChrg": 0.0,
            "TotItemVal": tot_item_val
        }
        items_list.append(item_dict)

    # 6. Value Details
    tot_ass_val = round(tot_ass_val, 2)
    tot_cgst = round(tot_cgst, 2)
    tot_sgst = round(tot_sgst, 2)
    tot_igst = round(tot_igst, 2)
    tot_inv_val = round(float(getattr(sale, "grand_total", None) or getattr(sale, "total_amount", None) or (tot_ass_val + tot_cgst + tot_sgst + tot_igst)), 2)
    calculated_total = round(tot_ass_val + tot_cgst + tot_sgst + tot_igst, 2)
    rnd_off_amt = round(tot_inv_val - calculated_total, 2)

    val_dtls = {
        "AssVal": tot_ass_val,
        "CgstVal": tot_cgst,
        "SgstVal": tot_sgst,
        "IgstVal": tot_igst,
        "CesVal": 0.0,
        "StCesVal": 0.0,
        "Discount": round(tot_discount, 2),
        "OthChrg": 0.0,
        "RndOffAmt": rnd_off_amt,
        "TotInvVal": tot_inv_val
    }

    # 7. Assembled INV-01 Payload
    payload = {
        "Version": "1.1",
        "TranDtls": {
            "TaxSch": "GST",
            "SupTyp": sup_typ,
            "RegRev": "N",
            "EcmGstin": None,
            "IgstOnIntra": "N"
        },
        "DocDtls": {
            "Typ": "INV",
            "No": doc_no,
            "Dt": formatted_date
        },
        "SellerDtls": {
            "Gstin": seller_gstin,
            "LglNm": seller_name,
            "TrdNm": seller_name,
            "Addr1": seller_addr[:100],
            "Loc": seller_state_name[:50],
            "Pin": seller_pin,
            "Stcd": seller_state_code,
            "Ph": seller_phone or None,
            "Em": seller_email or None
        },
        "BuyerDtls": {
            "Gstin": buyer_gstin,
            "LglNm": buyer_name,
            "TrdNm": buyer_name,
            "Pos": pos,
            "Addr1": buyer_addr[:100],
            "Loc": buyer_loc[:50],
            "Pin": buyer_pin,
            "Stcd": buyer_state_code,
            "Ph": clean_str(sale.customer_phone, max_len=12) or None,
            "Em": clean_str(sale.customer_email, max_len=100) or None
        },
        "ItemList": items_list,
        "ValDtls": val_dtls
    }

    # Optional Dispatch Details if origin warehouse is provided and has distinct address
    origin_wh_id = getattr(sale, "origin_warehouse_id", None)
    if origin_wh_id and db:
        wh = db.query(Warehouse).filter(Warehouse.id == origin_wh_id).first()
        if wh and wh.address and wh.address.strip():
            payload["DispDtls"] = {
                "Nm": wh.name[:100],
                "Addr1": wh.address[:100],
                "Loc": (wh.hub.city if wh.hub and wh.hub.city else "Warehouse")[:50],
                "Pin": clean_pin(wh.address),
                "Stcd": clean_state_code(wh.hub.state_code if wh.hub else seller_state_code)
            }

    return payload
