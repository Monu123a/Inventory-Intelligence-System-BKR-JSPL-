import os
import io
import csv
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.models.schema import (
    Sale, SaleItem, Product, Warehouse, Company,
    AmazonLiveAllocation, AmazonNetworkType, ReportHistory
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

REPORT_COLUMNS = [
    "SNO.",
    "BILL NO.",
    "ITEM CODE",
    "ITEM NAME",
    "hsn code",
    "GROUP11.GRP1",
    "BILL DATE",
    "GST NO.",
    "GST STATE NAME",
    "PARTY NAME",
    "PACK / SIZE",
    "SALE QUANTITY",
    "RATE/UNIT",
    "GROSS AMOUNT",
    "TOTAL SGST AMOUNT",
    "TOTAL CGST AMOUNT",
    "TOTAL IGST AMOUNT",
    "TD(%)",
    "CD(%)",
    "FREIGHT",
    "TAX-3(%)",
    "NET AMOUNT",
    "CD VALUE",
    "AMOUNT (USER DEFINED RATE)",
    "CREDIT",
    "CASH",
    "TAX REGION",
    "SCHEME(RS.)",
    "REMARKS-3",
    "REMARKS-1",
    "REMARKS-2",
    "RCU MOBILE NO.",
    "RCU EMAIL ID",
    "ADJUST/UNIT",
    "RCU DISCOUNT CARD NO.",
    "ORDER NO.",
    "GODOWN NAME",
    "PUR RATE",
    "RATE-1",
    "LOT PURCHASE RATE",
    "TRANSPORT MODE",
    "CREDIT NOTE DESC",
    "ADDRESS-1",
    "ADDRESS-2",
    "ADDRESS-3",
    "HSN CODE",
    "HSN DESCRIPTION"
]

class SeriesReportService:
    @staticmethod
    def get_detected_series(db: Session, company_id: Optional[int] = None) -> List[Dict[str, str]]:
        """Returns detected series / prefixes from existing sales and Amazon orders."""
        query = db.query(Sale.bill_number, Sale.invoice_number)
        if company_id:
            query = query.filter(Sale.company_id == company_id)
        
        sales = query.all()
        series_set = set()
        for b, inv in sales:
            ref = (inv or b or "").strip()
            if "-" in ref:
                prefix = ref.split("-")[0].strip().upper()
                if prefix:
                    series_set.add(prefix)
            elif ref and not ref.isdigit():
                series_set.add(ref[:3].upper())

        options = [
            {"id": "GST", "label": "GST Series (GST- / BKR-GST- / JGST-)"},
            {"id": "AMAZON", "label": "Amazon Series (SP-API & AFN/MFN Orders)"},
            {"id": "BKR", "label": "BKR Retail Series (BKR-)"},
            {"id": "JGST", "label": "JSPL GST Series (JGST-)"},
            {"id": "ALL", "label": "All Invoices & Series Combined"}
        ]
        
        # Add any other unique prefixes discovered
        for p in sorted(series_set):
            if p not in ("GST", "BKR", "JGST", "DELETED", "EDITED"):
                options.append({"id": p, "label": f"{p} Series ({p}-*)"})

        return options

    @staticmethod
    def generate_series_sales_report(
        db: Session,
        company_id: Optional[int] = None,
        series: str = "GST",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant Series-Wise Sales Report in the exact 47-column format.
        Returns: (file_data, filename, media_type, row_count)
        """
        series_clean = (series or "GST").strip().upper()
        
        # 1. Fetch Sales Matching Filter
        sales_query = db.query(Sale).filter(Sale.status != 'Cancelled')
        if company_id:
            sales_query = sales_query.filter(Sale.company_id == company_id)

        if date_from:
            sales_query = sales_query.filter(Sale.sale_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            sales_query = sales_query.filter(Sale.sale_date <= datetime.combine(date_to, datetime.max.time()))

        # Series matching logic
        if series_clean == "GST":
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike("GST%"),
                    Sale.invoice_number.ilike("GST%"),
                    Sale.bill_number.ilike("%GST%"),
                    Sale.invoice_number.ilike("%GST%"),
                    Sale.invoice_type == "B2B"
                )
            )
        elif series_clean == "AMAZON":
            sales_query = sales_query.filter(
                or_(
                    Sale.transaction_origin == "AMAZON",
                    Sale.bill_number.ilike("AMZ%"),
                    Sale.invoice_number.ilike("AMZ%"),
                    Sale.bill_number.ilike("%AMZN%"),
                    Sale.invoice_number.ilike("%AMZN%")
                )
            )
        elif series_clean == "BKR":
            sales_query = sales_query.filter(
                and_(
                    or_(Sale.bill_number.ilike("BKR%"), Sale.invoice_number.ilike("BKR%")),
                    ~Sale.bill_number.ilike("%GST%"),
                    ~Sale.invoice_number.ilike("%GST%")
                )
            )
        elif series_clean == "JGST":
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike("JGST%"),
                    Sale.invoice_number.ilike("JGST%"),
                    Sale.bill_number.ilike("JSPL%"),
                    Sale.invoice_number.ilike("JSPL%")
                )
            )
        elif series_clean == "ALL":
            pass # No series filter applied
        else:
            # Custom prefix provided by user
            pattern = f"{series_clean}%"
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike(pattern),
                    Sale.invoice_number.ilike(pattern)
                )
            )

        sales = sales_query.order_by(Sale.sale_date.asc(), Sale.id.asc()).all()

        # Check if Amazon live allocations should be appended for series="AMAZON" or "ALL"
        amazon_allocations = []
        if series_clean in ("AMAZON", "ALL"):
            alloc_query = db.query(AmazonLiveAllocation)
            if company_id:
                alloc_query = alloc_query.filter(AmazonLiveAllocation.company_id == company_id)
            amazon_allocations = alloc_query.order_by(AmazonLiveAllocation.id.asc()).all()

        # Date string formatting for Title
        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        title_str = f"SALE REPORT FOR ACCOUNTANT-{series_clean} From {d_from_str} to {d_to_str}"

        # Build Data Rows
        data_rows: List[List[Any]] = []
        sno = 0
        grand_qty = 0
        grand_gross = 0.0
        grand_sgst = 0.0
        grand_cgst = 0.0
        grand_igst = 0.0
        grand_net = 0.0
        grand_cost = 0.0
        grand_credit = 0.0
        grand_cash = 0.0

        for sale in sales:
            items = sale.items or []
            if not items:
                continue

            bill_no = sale.invoice_number or sale.bill_number
            bill_date = sale.sale_date.strftime("%d/%m/%Y") if sale.sale_date else ""
            party_name = sale.customer_name or "CUSTOMER A/C"
            gst_no = sale.customer_gstin or ""
            gst_state = sale.customer_state or "Chandigarh"

            # Parse addresses
            addr_parts = [p.strip() for p in (sale.customer_address or "").replace("\r", "\n").split("\n") if p.strip()]
            if not addr_parts:
                addr_parts = [p.strip() for p in (sale.customer_address or "").split(",") if p.strip()]
            
            addr1 = addr_parts[0] if len(addr_parts) > 0 else ""
            addr2 = addr_parts[1] if len(addr_parts) > 1 else ""
            addr3 = addr_parts[2] if len(addr_parts) > 2 else (sale.customer_state or "")

            bill_qty = 0
            bill_gross = 0.0
            bill_sgst = 0.0
            bill_cgst = 0.0
            bill_igst = 0.0
            bill_net = 0.0
            bill_cost = 0.0
            bill_credit = 0.0
            bill_cash = 0.0

            for it in items:
                sno += 1
                prod = it.product
                item_code = it.sku
                item_name = it.product_name or (prod.name if prod else it.sku)
                hsn_code = it.hsn_sac or (prod.hsn if prod else "") or ""
                pack_size = it.unit or (prod.unit if prod else "") or ""
                qty = it.quantity or 1

                gst_rate = float(it.gst_rate if it.gst_rate is not None else ((prod.default_gst_rate or 0) if prod else 0))
                if gst_rate == 0:
                    group_tax = "GST TAXFREE"
                else:
                    group_tax = f"GST {int(gst_rate) if gst_rate.is_integer() else gst_rate}%"

                # Calculate taxable gross and rate
                if it.taxable_amount and it.taxable_amount > 0:
                    gross_amt = round(float(it.taxable_amount), 2)
                    rate_unit = round(gross_amt / qty, 2)
                elif it.line_total and gst_rate > 0:
                    gross_amt = round(float(it.line_total) / (1 + (gst_rate / 100.0)), 2)
                    rate_unit = round(gross_amt / qty, 2)
                else:
                    rate_unit = round(float(it.selling_price or 0.0), 2)
                    gross_amt = round(rate_unit * qty, 2)

                # Tax amounts
                sgst = round(float(it.sgst or 0.0), 2)
                cgst = round(float(it.cgst or 0.0), 2)
                igst = round(float(it.igst or 0.0), 2)

                # Determine tax region and rates
                if igst > 0:
                    tax_region = "IGST"
                    tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                elif sgst > 0 or cgst > 0:
                    tax_region = "CGST/SGST"
                    half_rate = gst_rate / 2.0
                    tax_3 = int(half_rate) if half_rate.is_integer() else half_rate
                else:
                    # Deduce from address / state
                    is_interstate = bool(sale.customer_state and sale.customer_state.lower() != "chandigarh")
                    if is_interstate and gst_rate > 0:
                        tax_region = "IGST"
                        igst = round(gross_amt * (gst_rate / 100.0), 2)
                        tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                    elif gst_rate > 0:
                        tax_region = "CGST/SGST"
                        half_rate = gst_rate / 2.0
                        cgst = round(gross_amt * (half_rate / 100.0), 2)
                        sgst = round(gross_amt * (half_rate / 100.0), 2)
                        tax_3 = int(half_rate) if half_rate.is_integer() else half_rate
                    else:
                        tax_region = "CGST/SGST"
                        tax_3 = ""

                # Net amount
                if it.line_total and it.line_total > 0:
                    net_amt = round(float(it.line_total), 2)
                else:
                    net_amt = round(gross_amt + sgst + cgst + igst, 2)

                # Purchase cost / item rate
                pur_rate = float(prod.item_rate if prod and prod.item_rate else 0.0)
                pur_rate_str = f"{round(pur_rate, 2):g}" if pur_rate > 0 else ""
                rate_1_str = f"{pur_rate:.4f}" if pur_rate > 0 else ""
                cost_amt = round(pur_rate * qty, 2) if pur_rate > 0 else ""

                # Credit vs Cash distribution
                is_credit = bool(sale.customer_gstin) or sale.invoice_type == "B2B" or \
                            (sale.payment_method or "").lower() in ["credit", "unpaid", "bank transfer", "cheque", "neft", "rtgs"]
                
                credit_col = net_amt if is_credit else ""
                cash_col = net_amt if not is_credit else ""

                hsn_desc = (prod.category if prod and prod.category else "Other") or "Other"

                row = [
                    sno,                                       # 0: SNO.
                    bill_no,                                   # 1: BILL NO.
                    item_code,                                 # 2: ITEM CODE
                    item_name,                                 # 3: ITEM NAME
                    hsn_code,                                  # 4: hsn code
                    group_tax,                                 # 5: GROUP11.GRP1
                    bill_date,                                 # 6: BILL DATE
                    gst_no,                                    # 7: GST NO.
                    gst_state,                                 # 8: GST STATE NAME
                    party_name,                                # 9: PARTY NAME
                    pack_size,                                 # 10: PACK / SIZE
                    qty,                                       # 11: SALE QUANTITY
                    rate_unit,                                 # 12: RATE/UNIT
                    gross_amt,                                 # 13: GROSS AMOUNT
                    sgst if sgst > 0 else "",                  # 14: TOTAL SGST AMOUNT
                    cgst if cgst > 0 else "",                  # 15: TOTAL CGST AMOUNT
                    igst if igst > 0 else "",                  # 16: TOTAL IGST AMOUNT
                    "",                                        # 17: TD(%)
                    "",                                        # 18: CD(%)
                    "",                                        # 19: FREIGHT
                    tax_3,                                     # 20: TAX-3(%)
                    net_amt,                                   # 21: NET AMOUNT
                    "",                                        # 22: CD VALUE
                    cost_amt,                                  # 23: AMOUNT (USER DEFINED RATE)
                    credit_col,                                # 24: CREDIT
                    cash_col,                                  # 25: CASH
                    tax_region,                                # 26: TAX REGION
                    "",                                        # 27: SCHEME(RS.)
                    sale.payment_remarks or " ",               # 28: REMARKS-3
                    sale.payment_reference or " ",             # 29: REMARKS-1
                    " ",                                       # 30: REMARKS-2
                    sale.customer_mobile or "",                # 31: RCU MOBILE NO.
                    sale.customer_email or "",                 # 32: RCU EMAIL ID
                    "",                                        # 33: ADJUST/UNIT
                    "",                                        # 34: RCU DISCOUNT CARD NO.
                    sale.buyer_order_no or " ",                # 35: ORDER NO.
                    "",                                        # 36: GODOWN NAME
                    pur_rate_str,                              # 37: PUR RATE
                    rate_1_str,                                # 38: RATE-1
                    "",                                        # 39: LOT PURCHASE RATE
                    sale.dispatch_through or "",               # 40: TRANSPORT MODE
                    "",                                        # 41: CREDIT NOTE DESC
                    addr1,                                     # 42: ADDRESS-1
                    addr2,                                     # 43: ADDRESS-2
                    addr3,                                     # 44: ADDRESS-3
                    hsn_code,                                  # 45: HSN CODE
                    hsn_desc                                   # 46: HSN DESCRIPTION
                ]
                data_rows.append(row)

                # Accumulate
                bill_qty += qty
                bill_gross += gross_amt
                bill_sgst += sgst
                bill_cgst += cgst
                bill_igst += igst
                bill_net += net_amt
                if pur_rate > 0:
                    bill_cost += (pur_rate * qty)
                if is_credit:
                    bill_credit += net_amt
                else:
                    bill_cash += net_amt

            # Append Bill No. Wise Subtotal Row
            subtotal_row = [
                "",                                            # 0: SNO.
                "BILL NO. WISE TOTALS",                        # 1: BILL NO.
                "", "", "", "", "", "", "", "", "",            # 2-10: (empty)
                bill_qty,                                      # 11: SALE QUANTITY
                "",                                            # 12: RATE/UNIT
                round(bill_gross, 2),                          # 13: GROSS AMOUNT
                round(bill_sgst, 2) if bill_sgst > 0 else "",  # 14: TOTAL SGST AMOUNT
                round(bill_cgst, 2) if bill_cgst > 0 else "",  # 15: TOTAL CGST AMOUNT
                round(bill_igst, 2) if bill_igst > 0 else "",  # 16: TOTAL IGST AMOUNT
                "", "", "", "",                                # 17-20: (empty)
                round(bill_net, 2),                            # 21: NET AMOUNT
                "",                                            # 22: CD VALUE
                round(bill_cost, 2) if bill_cost > 0 else "",  # 23: AMOUNT (USER DEFINED RATE)
                round(bill_credit, 2) if bill_credit > 0 else "",# 24: CREDIT
                round(bill_cash, 2) if bill_cash > 0 else "",  # 25: CASH
                "", "", "", "", "", "", "", "", "", "",        # 26-35: (empty)
                "", "", "", "", "", "", "", "", "", "", ""     # 36-46: (empty)
            ]
            data_rows.append(subtotal_row)

            # Accumulate to Grand Total
            grand_qty += bill_qty
            grand_gross += bill_gross
            grand_sgst += bill_sgst
            grand_cgst += bill_cgst
            grand_igst += bill_igst
            grand_net += bill_net
            grand_cost += bill_cost
            grand_credit += bill_credit
            grand_cash += bill_cash

        # Process Amazon allocations if requested and no sales covered them
        if series_clean in ("AMAZON", "ALL") and amazon_allocations:
            for alloc in amazon_allocations:
                sno += 1
                prod = db.query(Product).filter(Product.sku == alloc.sku, Product.company_id == alloc.company_id).first()
                wh = db.query(Warehouse).filter(Warehouse.id == alloc.warehouse_id).first() if alloc.warehouse_id else None
                
                order_id = alloc.order_id
                item_code = alloc.sku
                item_name = prod.name if prod else alloc.sku
                hsn_code = prod.hsn if prod else ""
                pack_size = prod.unit if prod else ""
                qty = alloc.allocated_qty or 1
                
                gst_rate = float(prod.default_gst_rate or 18.0) if prod else 18.0
                group_tax = f"GST {int(gst_rate) if gst_rate.is_integer() else gst_rate}%"
                
                pur_rate = float(prod.item_rate if prod and prod.item_rate else 0.0)
                selling_price = pur_rate * 1.35 if pur_rate > 0 else 500.0
                rate_unit = round(selling_price / (1 + (gst_rate / 100.0)), 2)
                gross_amt = round(rate_unit * qty, 2)
                
                # Interstate IGST for Amazon FC orders
                igst = round(gross_amt * (gst_rate / 100.0), 2)
                tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                net_amt = round(gross_amt + igst, 2)
                cost_amt = round(pur_rate * qty, 2) if pur_rate > 0 else ""

                godown_name = wh.name if wh else (alloc.amazon_network_at_allocation.value if alloc.amazon_network_at_allocation else "Amazon AFN")
                hsn_desc = prod.category if prod and prod.category else "Other"

                row = [
                    sno,
                    order_id,
                    item_code,
                    item_name,
                    hsn_code,
                    group_tax,
                    datetime.utcnow().strftime("%d/%m/%Y"),
                    "",
                    wh.name.split()[-1] if wh and " " in wh.name else "Karnataka",
                    "Amazon Retail Customer",
                    pack_size,
                    qty,
                    rate_unit,
                    gross_amt,
                    "", "", igst if igst > 0 else "",
                    "", "", "", tax_3,
                    net_amt,
                    "",
                    cost_amt,
                    "",
                    net_amt, # Cash / Online Amazon payout
                    "IGST",
                    "", " ", f"AMZ-SYNC-{alloc.amazon_line_item_id or ''}", " ",
                    "", "", "", "",
                    order_id,
                    godown_name,
                    f"{round(pur_rate, 2):g}" if pur_rate > 0 else "",
                    f"{pur_rate:.4f}" if pur_rate > 0 else "",
                    "", "Amazon Logistics", "",
                    f"Amazon FC {godown_name}", "", "",
                    hsn_code,
                    hsn_desc
                ]
                data_rows.append(row)

                # Subtotal for single Amazon order
                subtotal_row = [
                    "",
                    "BILL NO. WISE TOTALS",
                    "", "", "", "", "", "", "", "", "",
                    qty,
                    "",
                    gross_amt,
                    "", "", igst if igst > 0 else "",
                    "", "", "", "",
                    net_amt,
                    "",
                    cost_amt,
                    "",
                    net_amt,
                    "", "", "", "", "", "", "", "", "", "",
                    "", "", "", "", "", "", "", "", "", "", ""
                ]
                data_rows.append(subtotal_row)

                grand_qty += qty
                grand_gross += gross_amt
                grand_igst += igst
                grand_net += net_amt
                if pur_rate > 0:
                    grand_cost += (pur_rate * qty)
                grand_cash += net_amt

        # Append Final Grand Totals Row
        grand_total_row = [
            "",                                                # 0: SNO.
            "GRAND TOTALS",                                    # 1: BILL NO.
            "", "", "", "", "", "", "", "", "",                # 2-10: (empty)
            grand_qty,                                         # 11: SALE QUANTITY
            "",                                                # 12: RATE/UNIT
            round(grand_gross, 2),                             # 13: GROSS AMOUNT
            round(grand_sgst, 2) if grand_sgst > 0 else "",    # 14: TOTAL SGST AMOUNT
            round(grand_cgst, 2) if grand_cgst > 0 else "",    # 15: TOTAL CGST AMOUNT
            round(grand_igst, 2) if grand_igst > 0 else "",    # 16: TOTAL IGST AMOUNT
            "", "", "", "",                                    # 17-20: (empty)
            round(grand_net, 2),                               # 21: NET AMOUNT
            "",                                                # 22: CD VALUE
            round(grand_cost, 2) if grand_cost > 0 else "",    # 23: AMOUNT (USER DEFINED RATE)
            round(grand_credit, 2) if grand_credit > 0 else "",# 24: CREDIT
            round(grand_cash, 2) if grand_cash > 0 else "",    # 25: CASH
            "", "", "", "", "", "", "", "", "", "",            # 26-35: (empty)
            "", "", "", "", "", "", "", "", "", "", ""         # 36-46: (empty)
        ]
        data_rows.append(grand_total_row)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_base = f"Accountant_Sales_{series_clean}_{timestamp_str}"

        # Generate CSV or Excel Output
        if file_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Row 1: 46 commas (47 empty columns)
            writer.writerow([""] * 47)
            # Row 2: Title repeated across 47 columns
            writer.writerow([title_str] * 47)
            # Row 3: 47 Column Headers
            writer.writerow(REPORT_COLUMNS)
            # Data & Subtotals & Grand Total Rows
            for r in data_rows:
                writer.writerow(r)

            content = output.getvalue()
            filename = f"{filename_base}.csv"
            media_type = "text/csv"

            # Save to Reports Dir and Log in ReportHistory
            filepath = os.path.join(REPORTS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            if company_id:
                rep_hist = ReportHistory(
                    company_id=company_id,
                    report_type=f"Accountant Sales ({series_clean})",
                    file_path=filepath,
                    download_link=f"/api/reports/download/{filename}"
                )
                db.add(rep_hist)
                db.commit()

            return content, filename, media_type, len(data_rows)

        else:
            # Excel (.xlsx) formatting via openpyxl
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"{series_clean[:10]}_Sales"

            # Row 1: empty row
            ws.append([""] * 47)

            # Row 2: Title banner merged across columns
            ws.append([title_str] * 47)
            title_cell = ws.cell(row=2, column=1)
            title_cell.font = Font(name="Calibri", size=11, bold=True, color="1E293B")
            title_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            for c in range(1, 48):
                ws.cell(row=2, column=c).fill = title_fill

            # Row 3: Header Row
            ws.append(REPORT_COLUMNS)
            header_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            header_font = Font(name="Calibri", size=10, bold=True, color="0F172A")
            for c in range(1, 48):
                cell = ws.cell(row=3, column=c)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            thin_border = Border(
                left=Side(style='thin', color='E2E8F0'),
                right=Side(style='thin', color='E2E8F0'),
                top=Side(style='thin', color='E2E8F0'),
                bottom=Side(style='thin', color='E2E8F0')
            )
            subtotal_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            grand_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

            # Append Data Rows
            current_row_idx = 4
            for r in data_rows:
                ws.append(r)
                is_subtotal = (r[1] == "BILL NO. WISE TOTALS")
                is_grand = (r[1] == "GRAND TOTALS")

                for c_idx in range(1, 48):
                    cell = ws.cell(row=current_row_idx, column=c_idx)
                    cell.border = thin_border
                    if is_grand:
                        cell.font = Font(name="Calibri", size=10, bold=True, color="92400E")
                        cell.fill = grand_fill
                    elif is_subtotal:
                        cell.font = Font(name="Calibri", size=10, bold=True, color="1E293B")
                        cell.fill = subtotal_fill
                    else:
                        cell.font = Font(name="Calibri", size=10, color="334155")

                    # Right-align numeric columns
                    if c_idx in (12, 13, 14, 15, 16, 17, 21, 22, 24, 25, 26, 38, 39):
                        cell.alignment = Alignment(horizontal="right")

                current_row_idx += 1

            # Auto-fit column widths (with sane caps)
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col[2:]: # Check from header downwards
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

            stream = io.BytesIO()
            wb.save(stream)
            excel_bytes = stream.getvalue()

            filename = f"{filename_base}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            filepath = os.path.join(REPORTS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(excel_bytes)

            if company_id:
                rep_hist = ReportHistory(
                    company_id=company_id,
                    report_type=f"Accountant Sales ({series_clean})",
                    file_path=filepath,
                    download_link=f"/api/reports/download/{filename}"
                )
                db.add(rep_hist)
                db.commit()

            return excel_bytes, filename, media_type, len(data_rows)
