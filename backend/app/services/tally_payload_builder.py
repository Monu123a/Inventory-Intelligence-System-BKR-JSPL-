from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from app.models.schema import Sale


class TallyPayloadBuilder:
    """
    Pure transformation: Sale -> payload (no networking).
    This is intentionally decoupled so later we can swap Sale->Invoice domain
    without changing integration workflow.
    """

    @staticmethod
    def build_json(sale: Sale) -> Dict[str, Any]:
        return {
            "invoice_number": sale.invoice_number,
            "bill_number": sale.bill_number,
            "invoice_type": sale.invoice_type,
            "invoice_date": sale.sale_date.isoformat() if sale.sale_date else datetime.utcnow().isoformat(),
            "company": {
                "name": sale.company_name_snapshot,
                "gstin": sale.company_gstin_snapshot,
                "address": sale.company_address_snapshot,
                "state": sale.company_state_snapshot,
                "state_code": sale.company_state_code_snapshot,
            },
            "customer": {
                "name": sale.customer_name,
                "gstin": sale.customer_gstin,
                "address": sale.customer_address,
                "state": sale.customer_state,
                "state_code": sale.customer_state_code,
                "place_of_supply": sale.place_of_supply,
                "phone": sale.customer_phone,
                "email": sale.customer_email,
            },
            "totals": {
                "taxable": sale.total_taxable_amount,
                "tax": sale.total_tax,
                "grand_total": sale.grand_total,
            },
            "items": [
                {
                    "sku": i.sku,
                    "name": i.product_name,
                    "hsn_sac": i.hsn_sac,
                    "gst_rate": i.gst_rate,
                    "quantity": i.quantity,
                    "unit": i.unit,
                    "rate": i.selling_price,
                    "discount": i.discount,
                    "taxable_value": i.taxable_amount,
                    "cgst": i.cgst,
                    "sgst": i.sgst,
                    "igst": i.igst,
                    "line_total": i.line_total,
                }
                for i in (sale.items or [])
            ],
        }

    @staticmethod
    def build_xml(sale: Sale) -> str:
        """
        Minimal generic XML placeholder. Real TallyPrime XML can be configured later.
        """
        inv_no = sale.invoice_number or sale.bill_number
        inv_dt = sale.sale_date.strftime("%Y%m%d") if sale.sale_date else datetime.utcnow().strftime("%Y%m%d")
        amount = f"{sale.grand_total or 0:.2f}"

        # Note: intentionally generic and not Tally-branded.
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
  <InvoiceNumber>{inv_no}</InvoiceNumber>
  <InvoiceDate>{inv_dt}</InvoiceDate>
  <InvoiceType>{sale.invoice_type or "B2C"}</InvoiceType>
  <CompanyName>{sale.company_name_snapshot or ""}</CompanyName>
  <CompanyGSTIN>{sale.company_gstin_snapshot or ""}</CompanyGSTIN>
  <CustomerName>{sale.customer_name or ""}</CustomerName>
  <CustomerGSTIN>{sale.customer_gstin or ""}</CustomerGSTIN>
  <GrandTotal>{amount}</GrandTotal>
</Invoice>
"""

