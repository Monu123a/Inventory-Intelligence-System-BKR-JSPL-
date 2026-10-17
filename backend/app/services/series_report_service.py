import os
import io
import csv
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import or_, and_, func

from app.models.schema import (
    Sale, SaleItem, Product, Warehouse, Company,
    AmazonLiveAllocation, AmazonNetworkType, ReportHistory,
    Purchase, PurchaseItem, Vendor,
    SalesReturn, SalesReturnItem, AmazonReturn,
    FCReturn, FCReturnItem, InventoryMovement
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

STATE_CODE_MAP = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh"
}

def deduce_state_from_gstin(gstin: Optional[str], fallback: str = "Chandigarh") -> str:
    if gstin and len(gstin.strip()) >= 2:
        code = gstin.strip()[:2]
        if code in STATE_CODE_MAP:
            return STATE_CODE_MAP[code]
    return fallback

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
    def _export_dataset(
        db: Session,
        company_id: Optional[int],
        data_rows: List[List[Any]],
        title_str: str,
        filename_base: str,
        sheet_title: str,
        report_type_label: str,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Shared exporter converting 47-column data rows into CSV or styled Excel (.xlsx).
        """
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
                    report_type=report_type_label,
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
            ws.title = sheet_title[:31]

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
            # Append Data Rows & track column widths simultaneously
            col_widths = {c: len(str(REPORT_COLUMNS[c-1])) for c in range(1, 48)}
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

                    val_len = len(str(r[c_idx-1] or ''))
                    if val_len > col_widths[c_idx]:
                        col_widths[c_idx] = val_len

                current_row_idx += 1

            # Auto-fit column widths using tracked maximums
            for c_idx, max_len in col_widths.items():
                col_letter = get_column_letter(c_idx)
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
                    report_type=report_type_label,
                    file_path=filepath,
                    download_link=f"/api/reports/download/{filename}"
                )
                db.add(rep_hist)
                db.commit()

            return excel_bytes, filename, media_type, len(data_rows)

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
            pass
        else:
            pattern = f"{series_clean}%"
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike(pattern),
                    Sale.invoice_number.ilike(pattern)
                )
            )

        sales_query = sales_query.options(
            selectinload(Sale.items).selectinload(SaleItem.product)
        )
        sales = sales_query.order_by(Sale.sale_date.asc(), Sale.id.asc()).all()

        amazon_allocations = []
        if series_clean in ("AMAZON", "ALL"):
            alloc_query = db.query(AmazonLiveAllocation)
            if company_id:
                has_allocs = db.query(AmazonLiveAllocation.id).filter(AmazonLiveAllocation.company_id == company_id).first()
                if has_allocs:
                    alloc_query = alloc_query.filter(AmazonLiveAllocation.company_id == company_id)
            if date_from:
                alloc_query = alloc_query.filter(AmazonLiveAllocation.created_at >= datetime.combine(date_from, datetime.min.time()))
            if date_to:
                alloc_query = alloc_query.filter(AmazonLiveAllocation.created_at <= datetime.combine(date_to, datetime.max.time()))
            amazon_allocations = alloc_query.order_by(AmazonLiveAllocation.created_at.asc(), AmazonLiveAllocation.id.asc()).all()

        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        title_str = f"SALE REPORT FOR ACCOUNTANT-{series_clean} From {d_from_str} to {d_to_str}"

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
            gst_state = sale.customer_state or deduce_state_from_gstin(gst_no, "Chandigarh")

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

                if it.taxable_amount and it.taxable_amount > 0:
                    gross_amt = round(float(it.taxable_amount), 2)
                    rate_unit = round(gross_amt / qty, 2)
                elif it.line_total and gst_rate > 0:
                    gross_amt = round(float(it.line_total) / (1 + (gst_rate / 100.0)), 2)
                    rate_unit = round(gross_amt / qty, 2)
                else:
                    rate_unit = round(float(it.selling_price or 0.0), 2)
                    gross_amt = round(rate_unit * qty, 2)

                sgst = round(float(it.sgst or 0.0), 2)
                cgst = round(float(it.cgst or 0.0), 2)
                igst = round(float(it.igst or 0.0), 2)

                if igst > 0:
                    tax_region = "IGST"
                    tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                elif sgst > 0 or cgst > 0:
                    tax_region = "CGST/SGST"
                    half_rate = gst_rate / 2.0
                    tax_3 = int(half_rate) if half_rate.is_integer() else half_rate
                else:
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

                if it.line_total and it.line_total > 0:
                    net_amt = round(float(it.line_total), 2)
                else:
                    net_amt = round(gross_amt + sgst + cgst + igst, 2)

                pur_rate = float(prod.item_rate if prod and prod.item_rate else 0.0)
                pur_rate_str = f"{round(pur_rate, 2):g}" if pur_rate > 0 else ""
                rate_1_str = f"{pur_rate:.4f}" if pur_rate > 0 else ""
                cost_amt = round(pur_rate * qty, 2) if pur_rate > 0 else ""

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

            grand_qty += bill_qty
            grand_gross += bill_gross
            grand_sgst += bill_sgst
            grand_cgst += bill_cgst
            grand_igst += bill_igst
            grand_net += bill_net
            grand_cost += bill_cost
            grand_credit += bill_credit
            grand_cash += bill_cash

        # Process Amazon allocations
        if series_clean in ("AMAZON", "ALL") and amazon_allocations:
            prod_query = db.query(Product)
            if company_id:
                prod_query = prod_query.filter(Product.company_id == company_id)
            prod_map = {p.sku.upper(): p for p in prod_query.all()}
            wh_map = {w.id: w for w in db.query(Warehouse).all()}

            for alloc in amazon_allocations:
                sno += 1
                prod = prod_map.get((alloc.sku or "").upper())
                wh = wh_map.get(alloc.warehouse_id) if alloc.warehouse_id else None
                
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
                
                igst = round(gross_amt * (gst_rate / 100.0), 2)
                tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                net_amt = round(gross_amt + igst, 2)
                cost_amt = round(pur_rate * qty, 2) if pur_rate > 0 else ""

                godown_name = wh.name if wh else (alloc.amazon_network_at_allocation.value if alloc.amazon_network_at_allocation else "Amazon AFN")
                hsn_desc = prod.category if prod and prod.category else "Other"

                alloc_dt = alloc.created_at.strftime("%d/%m/%Y") if alloc.created_at else datetime.utcnow().strftime("%d/%m/%Y")
                row = [
                    sno, order_id, item_code, item_name, hsn_code, group_tax,
                    alloc_dt, "",
                    wh.name.split()[-1] if wh and " " in wh.name else "Karnataka",
                    "Amazon Retail Customer", pack_size, qty, rate_unit, gross_amt,
                    "", "", igst if igst > 0 else "",
                    "", "", "", tax_3, net_amt, "", cost_amt, "",
                    net_amt, "IGST", "", " ", f"AMZ-SYNC-{alloc.amazon_line_item_id or ''}", " ",
                    "", "", "", "", order_id, godown_name,
                    f"{round(pur_rate, 2):g}" if pur_rate > 0 else "",
                    f"{pur_rate:.4f}" if pur_rate > 0 else "",
                    "", "Amazon Logistics", "", f"Amazon FC {godown_name}", "", "",
                    hsn_code, hsn_desc
                ]
                data_rows.append(row)

                subtotal_row = [
                    "", "BILL NO. WISE TOTALS",
                    "", "", "", "", "", "", "", "", "",
                    qty, "", gross_amt, "", "", igst if igst > 0 else "",
                    "", "", "", "", net_amt, "", cost_amt, "",
                    net_amt, "", "", "", "", "", "", "", "", "", "",
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

        # Final Grand Totals Row
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

        return SeriesReportService._export_dataset(
            db=db,
            company_id=company_id,
            data_rows=data_rows,
            title_str=title_str,
            filename_base=filename_base,
            sheet_title=f"{series_clean[:10]}_Sales",
            report_type_label=f"Accountant Sales ({series_clean})",
            file_format=file_format
        )

    @staticmethod
    def generate_purchase_report(
        db: Session,
        company_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Official Accountant Purchase Register in the exact 47-column format.
        Includes Bill No. Wise Totals and Grand Totals.
        """
        query = db.query(Purchase)
        if company_id:
            query = query.filter(Purchase.company_id == company_id)
        if vendor_id:
            query = query.filter(Purchase.vendor_id == vendor_id)
        if date_from:
            query = query.filter(func.coalesce(Purchase.date, Purchase.created_at) >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(func.coalesce(Purchase.date, Purchase.created_at) <= datetime.combine(date_to, datetime.max.time()))

        query = query.options(
            selectinload(Purchase.items),
            selectinload(Purchase.vendor)
        )
        purchases = query.order_by(func.coalesce(Purchase.date, Purchase.created_at).asc(), Purchase.id.asc()).all()

        # Pre-cache products, warehouses, and inventory movements in memory for O(1) instant lookups
        prod_map = {prod.sku.upper(): prod for prod in db.query(Product).all()}
        wh_map = {w.id: w for w in db.query(Warehouse).all()}
        mov_query = db.query(InventoryMovement).filter(InventoryMovement.source == "PURCHASE")
        if company_id:
            mov_query = mov_query.filter(InventoryMovement.company_id == company_id)
        movements = mov_query.all()
        mov_map = {m.reference_id: m for m in movements if m.reference_id}

        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        title_str = f"PURCHASE REGISTER FOR ACCOUNTANT From {d_from_str} to {d_to_str}"

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

        for p in purchases:
            items = p.items or []
            if not items:
                continue

            bill_no = p.invoice_number or f"PUR-{p.id}"
            p_date = p.date or p.created_at
            bill_date = p_date.strftime("%d/%m/%Y") if p_date else ""
            vendor = p.vendor
            party_name = vendor.name if vendor else (p.vendor_name or "Vendor A/C")
            gst_no = vendor.gst_number if vendor and vendor.gst_number else ""
            gst_state = deduce_state_from_gstin(gst_no, "Chandigarh")

            addr_parts = [part.strip() for part in (vendor.address or "").replace("\r", "\n").split("\n") if part.strip()] if vendor else []
            addr1 = addr_parts[0] if len(addr_parts) > 0 else ""
            addr2 = addr_parts[1] if len(addr_parts) > 1 else ""
            addr3 = addr_parts[2] if len(addr_parts) > 2 else gst_state

            # Find warehouse name
            mov = mov_map.get(bill_no)
            wh = wh_map.get(mov.warehouse_id) if mov else None
            godown_name = wh.name if wh else "Central Warehouse"

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
                prod = prod_map.get(it.product_sku)
                item_code = it.product_sku
                item_name = it.description or (prod.name if prod else it.product_sku)
                hsn_code = it.hsn or (prod.hsn if prod else "") or ""
                pack_size = prod.unit if prod else "PCS"
                qty = float(it.qty or 0)
                rate_unit = float(it.unit_cost or 0)
                gross_amt = round(qty * rate_unit, 2)
                gst_rate = float(it.gst_pct or 0)

                group_tax = "GST TAXFREE" if gst_rate == 0 else f"GST {int(gst_rate) if gst_rate.is_integer() else gst_rate}%"

                # Tax calculation (Interstate vs Intrastate)
                is_interstate = (gst_no and not gst_no.startswith("04")) or (gst_state.lower() != "chandigarh")
                if is_interstate and gst_rate > 0:
                    tax_region = "IGST"
                    igst = round(gross_amt * (gst_rate / 100.0), 2)
                    cgst = 0.0
                    sgst = 0.0
                    tax_3 = int(gst_rate) if gst_rate.is_integer() else gst_rate
                elif gst_rate > 0:
                    tax_region = "CGST/SGST"
                    half_rate = gst_rate / 2.0
                    cgst = round(gross_amt * (half_rate / 100.0), 2)
                    sgst = round(gross_amt * (half_rate / 100.0), 2)
                    igst = 0.0
                    tax_3 = int(half_rate) if half_rate.is_integer() else half_rate
                else:
                    tax_region = "CGST/SGST"
                    igst = 0.0
                    cgst = 0.0
                    sgst = 0.0
                    tax_3 = ""

                net_amt = round(float(it.line_total or (gross_amt + igst + cgst + sgst)), 2)

                is_credit = (p.payment_status != "PAID")
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
                    qty,                                       # 11: SALE QUANTITY (Purchased Qty)
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
                    gross_amt,                                 # 23: AMOUNT (USER DEFINED RATE)
                    credit_col,                                # 24: CREDIT
                    cash_col,                                  # 25: CASH
                    tax_region,                                # 26: TAX REGION
                    "",                                        # 27: SCHEME(RS.)
                    p.payment_terms or " ",                    # 28: REMARKS-3
                    p.notes or " ",                            # 29: REMARKS-1
                    p.eway_bill or " ",                        # 30: REMARKS-2
                    vendor.phone if vendor and vendor.phone else "", # 31: RCU MOBILE NO.
                    "",                                        # 32: RCU EMAIL ID
                    "",                                        # 33: ADJUST/UNIT
                    "",                                        # 34: RCU DISCOUNT CARD NO.
                    bill_no,                                   # 35: ORDER NO.
                    godown_name,                               # 36: GODOWN NAME
                    f"{round(rate_unit, 2):g}" if rate_unit > 0 else "", # 37: PUR RATE
                    f"{rate_unit:.4f}" if rate_unit > 0 else "",         # 38: RATE-1
                    "",                                        # 39: LOT PURCHASE RATE
                    p.vehicle_number or "",                    # 40: TRANSPORT MODE
                    "",                                        # 41: CREDIT NOTE DESC
                    addr1,                                     # 42: ADDRESS-1
                    addr2,                                     # 43: ADDRESS-2
                    addr3,                                     # 44: ADDRESS-3
                    hsn_code,                                  # 45: HSN CODE
                    hsn_desc                                   # 46: HSN DESCRIPTION
                ]
                data_rows.append(row)

                bill_qty += qty
                bill_gross += gross_amt
                bill_sgst += sgst
                bill_cgst += cgst
                bill_igst += igst
                bill_net += net_amt
                bill_cost += gross_amt
                if is_credit:
                    bill_credit += net_amt
                else:
                    bill_cash += net_amt

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

            grand_qty += bill_qty
            grand_gross += bill_gross
            grand_sgst += bill_sgst
            grand_cgst += bill_cgst
            grand_igst += bill_igst
            grand_net += bill_net
            grand_cost += bill_cost
            grand_credit += bill_credit
            grand_cash += bill_cash

        # Grand Totals Row
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
        filename_base = f"Accountant_Purchases_{timestamp_str}"

        return SeriesReportService._export_dataset(
            db=db,
            company_id=company_id,
            data_rows=data_rows,
            title_str=title_str,
            filename_base=filename_base,
            sheet_title="Purchase_Register",
            report_type_label="Accountant Purchases",
            file_format=file_format
        )

    @staticmethod
    def generate_amazon_returns_report(
        db: Session,
        company_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant Amazon Returns Register in the exact 47-column format.
        """
        query = db.query(AmazonReturn)
        if company_id:
            query = query.filter(AmazonReturn.company_id == company_id)
        if date_from:
            query = query.filter(func.coalesce(AmazonReturn.received_at, AmazonReturn.requested_at, AmazonReturn.created_at) >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(func.coalesce(AmazonReturn.received_at, AmazonReturn.requested_at, AmazonReturn.created_at) <= datetime.combine(date_to, datetime.max.time()))

        returns = query.order_by(func.coalesce(AmazonReturn.received_at, AmazonReturn.created_at).asc(), AmazonReturn.id.asc()).all()

        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        title_str = f"AMAZON RETURNS REPORT FOR ACCOUNTANT From {d_from_str} to {d_to_str}"

        # Pre-cache products in memory
        prod_map = {prod.sku: prod for prod in db.query(Product).all()}

        data_rows: List[List[Any]] = []
        sno = 0
        grand_qty = 0
        grand_gross = 0.0
        grand_igst = 0.0
        grand_net = 0.0

        for r in returns:
            sno += 1
            bill_no = r.amazon_return_id or r.amazon_order_id or f"AMZ-RET-{r.id}"
            r_date = r.received_at or r.requested_at or r.created_at
            bill_date = r_date.strftime("%d/%m/%Y") if r_date else ""
            
            prod = prod_map.get(r.sku)
            item_code = r.sku
            item_name = r.product_name or (prod.name if prod else r.sku)
            hsn_code = prod.hsn if prod else ""
            pack_size = prod.unit if prod else "PCS"
            qty = r.quantity or 1

            gst_rate = float(prod.default_gst_rate or 18.0) if prod else 18.0
            group_tax = f"GST {int(gst_rate) if gst_rate.is_integer() else gst_rate}%"

            pur_rate = float(prod.item_rate if prod and prod.item_rate else 0.0)
            selling_price = pur_rate * 1.35 if pur_rate > 0 else 500.0
            rate_unit = round(selling_price / (1 + (gst_rate / 100.0)), 2)
            gross_amt = round(rate_unit * qty, 2)
            igst = round(gross_amt * (gst_rate / 100.0), 2)
            net_amt = round(gross_amt + igst, 2)

            hsn_desc = prod.category if prod and prod.category else "Other"

            row = [
                sno,                                       # 0: SNO.
                bill_no,                                   # 1: BILL NO.
                item_code,                                 # 2: ITEM CODE
                item_name,                                 # 3: ITEM NAME
                hsn_code,                                  # 4: hsn code
                group_tax,                                 # 5: GROUP11.GRP1
                bill_date,                                 # 6: BILL DATE
                "",                                        # 7: GST NO.
                "Karnataka",                               # 8: GST STATE NAME
                "Amazon Retail Customer",                  # 9: PARTY NAME
                pack_size,                                 # 10: PACK / SIZE
                qty,                                       # 11: SALE QUANTITY (Returned Qty)
                rate_unit,                                 # 12: RATE/UNIT
                gross_amt,                                 # 13: GROSS AMOUNT
                "",                                        # 14: TOTAL SGST AMOUNT
                "",                                        # 15: TOTAL CGST AMOUNT
                igst if igst > 0 else "",                  # 16: TOTAL IGST AMOUNT
                "", "", "", gst_rate,                      # 17-20: TD, CD, Freight, Tax-3%
                net_amt,                                   # 21: NET AMOUNT
                "",                                        # 22: CD VALUE
                round(pur_rate * qty, 2) if pur_rate > 0 else "", # 23: AMOUNT (USER DEFINED RATE)
                net_amt,                                   # 24: CREDIT (Return Credit Note)
                "",                                        # 25: CASH
                "IGST",                                    # 26: TAX REGION
                "",                                        # 27: SCHEME(RS.)
                f"Status: {r.return_status or 'Received'}",# 28: REMARKS-3
                f"Inspection: {r.inspection_status or 'Pending'}", # 29: REMARKS-1
                r.inspection_notes or " ",                 # 30: REMARKS-2
                "", "", "", "",                            # 31-34: mobile, email, adjust, disc
                r.amazon_order_id or " ",                  # 35: ORDER NO.
                "Amazon AFN Return Hub",                   # 36: GODOWN NAME
                f"{round(pur_rate, 2):g}" if pur_rate > 0 else "", # 37: PUR RATE
                f"{pur_rate:.4f}" if pur_rate > 0 else "", # 38: RATE-1
                "",                                        # 39: LOT PURCHASE RATE
                "Amazon Return Logistics",                 # 40: TRANSPORT MODE
                r.return_reason or "Amazon Customer Return", # 41: CREDIT NOTE DESC
                "Amazon Fulfillment Network",              # 42: ADDRESS-1
                "", "",                                    # 43-44: ADDRESS-2, 3
                hsn_code,                                  # 45: HSN CODE
                hsn_desc                                   # 46: HSN DESCRIPTION
            ]
            data_rows.append(row)

            # Subtotal row
            subtotal_row = [
                "", "BILL NO. WISE TOTALS",
                "", "", "", "", "", "", "", "", "",
                qty, "", gross_amt, "", "", igst if igst > 0 else "",
                "", "", "", "", net_amt, "", "", net_amt, "",
                "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "", ""
            ]
            data_rows.append(subtotal_row)

            grand_qty += qty
            grand_gross += gross_amt
            grand_igst += igst
            grand_net += net_amt

        # Grand Totals Row
        grand_total_row = [
            "",                                                # 0: SNO.
            "GRAND TOTALS",                                    # 1: BILL NO.
            "", "", "", "", "", "", "", "", "",                # 2-10: (empty)
            grand_qty,                                         # 11: SALE QUANTITY
            "",                                                # 12: RATE/UNIT
            round(grand_gross, 2),                             # 13: GROSS AMOUNT
            "",                                                # 14: TOTAL SGST AMOUNT
            "",                                                # 15: TOTAL CGST AMOUNT
            round(grand_igst, 2) if grand_igst > 0 else "",    # 16: TOTAL IGST AMOUNT
            "", "", "", "",                                    # 17-20: (empty)
            round(grand_net, 2),                               # 21: NET AMOUNT
            "", "",                                            # 22-23: (empty)
            round(grand_net, 2),                               # 24: CREDIT
            "",                                                # 25: CASH
            "", "", "", "", "", "", "", "", "", "",            # 26-35: (empty)
            "", "", "", "", "", "", "", "", "", "", ""         # 36-46: (empty)
        ]
        data_rows.append(grand_total_row)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_base = f"Accountant_Amazon_Returns_{timestamp_str}"

        return SeriesReportService._export_dataset(
            db=db,
            company_id=company_id,
            data_rows=data_rows,
            title_str=title_str,
            filename_base=filename_base,
            sheet_title="Amazon_Returns",
            report_type_label="Accountant Amazon Returns",
            file_format=file_format
        )

    @staticmethod
    def generate_sales_returns_report(
        db: Session,
        company_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant POS Sales Returns / Credit Notes Register in the exact 47-column format.
        """
        query = db.query(SalesReturn)
        if company_id:
            query = query.filter(SalesReturn.company_id == company_id)
        if date_from:
            query = query.filter(func.coalesce(SalesReturn.return_date, SalesReturn.created_at) >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(func.coalesce(SalesReturn.return_date, SalesReturn.created_at) <= datetime.combine(date_to, datetime.max.time()))

        query = query.options(
            selectinload(SalesReturn.items).selectinload(SalesReturnItem.product)
        )
        returns = query.order_by(func.coalesce(SalesReturn.return_date, SalesReturn.created_at).asc(), SalesReturn.id.asc()).all()

        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        title_str = f"SALES RETURN REGISTER (CREDIT NOTES) From {d_from_str} to {d_to_str}"

        data_rows: List[List[Any]] = []
        sno = 0
        grand_qty = 0
        grand_gross = 0.0
        grand_sgst = 0.0
        grand_cgst = 0.0
        grand_igst = 0.0
        grand_net = 0.0

        for ret in returns:
            items = ret.items or []
            if not items:
                continue

            bill_no = ret.return_number or f"CN-{ret.id}"
            r_date = ret.return_date or ret.created_at
            bill_date = r_date.strftime("%d/%m/%Y") if r_date else ""
            party_name = ret.customer_name or "Retail Customer A/C"

            bill_qty = 0
            bill_gross = 0.0
            bill_sgst = 0.0
            bill_cgst = 0.0
            bill_igst = 0.0
            bill_net = 0.0

            for it in items:
                sno += 1
                item_code = it.sku_snapshot
                item_name = it.product_name_snapshot
                hsn_code = it.hsn_snapshot or ""
                pack_size = it.unit_snapshot or "PCS"
                qty = it.returned_quantity or 1
                rate_unit = float(it.unit_price or 0.0)
                gross_amt = round(qty * rate_unit, 2)
                gst_rate = float(it.tax_rate or 0.0)
                group_tax = "GST TAXFREE" if gst_rate == 0 else f"GST {int(gst_rate) if gst_rate.is_integer() else gst_rate}%"

                # Intrastate retail return default
                half_rate = gst_rate / 2.0
                cgst = round(gross_amt * (half_rate / 100.0), 2)
                sgst = round(gross_amt * (half_rate / 100.0), 2)
                igst = 0.0
                tax_3 = int(half_rate) if half_rate.is_integer() else half_rate
                net_amt = round(float(it.total_price or (gross_amt + cgst + sgst)), 2)

                row = [
                    sno, bill_no, item_code, item_name, hsn_code, group_tax,
                    bill_date, "", "Chandigarh", party_name, pack_size,
                    qty, rate_unit, gross_amt,
                    sgst if sgst > 0 else "", cgst if cgst > 0 else "", "",
                    "", "", "", tax_3, net_amt, "", gross_amt,
                    net_amt, "", "CGST/SGST", "", " ", " ", " ",
                    "", "", "", "", f"Sale #{ret.sale_id}" if ret.sale_id else " ",
                    "Central Warehouse", f"{round(rate_unit, 2):g}", f"{rate_unit:.4f}",
                    "", "", it.return_reason or ret.return_type or "Sales Return",
                    "", "", "", hsn_code, "Other"
                ]
                data_rows.append(row)

                bill_qty += qty
                bill_gross += gross_amt
                bill_sgst += sgst
                bill_cgst += cgst
                bill_net += net_amt

            subtotal_row = [
                "", "BILL NO. WISE TOTALS",
                "", "", "", "", "", "", "", "", "",
                bill_qty, "", round(bill_gross, 2),
                round(bill_sgst, 2) if bill_sgst > 0 else "",
                round(bill_cgst, 2) if bill_cgst > 0 else "",
                "", "", "", "", "", round(bill_net, 2), "", "",
                round(bill_net, 2), "", "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "", ""
            ]
            data_rows.append(subtotal_row)

            grand_qty += bill_qty
            grand_gross += bill_gross
            grand_sgst += bill_sgst
            grand_cgst += bill_cgst
            grand_net += bill_net

        grand_total_row = [
            "", "GRAND TOTALS",
            "", "", "", "", "", "", "", "", "",
            grand_qty, "", round(grand_gross, 2),
            round(grand_sgst, 2) if grand_sgst > 0 else "",
            round(grand_cgst, 2) if grand_cgst > 0 else "",
            "", "", "", "", "", round(grand_net, 2), "", "",
            round(grand_net, 2), "", "", "", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "", "", "", ""
        ]
        data_rows.append(grand_total_row)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_base = f"Accountant_Sales_Returns_{timestamp_str}"

        return SeriesReportService._export_dataset(
            db=db,
            company_id=company_id,
            data_rows=data_rows,
            title_str=title_str,
            filename_base=filename_base,
            sheet_title="Sales_Returns",
            report_type_label="Accountant Sales Returns",
            file_format=file_format
        )

    @staticmethod
    def generate_accountant_report(
        db: Session,
        report_type: str = "sales",
        company_id: Optional[int] = None,
        series: str = "GST",
        vendor_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Master dispatcher generating the requested report category in the exact 47-column accountant format.
        """
        rt = (report_type or "sales").strip().lower()
        if rt in ("purchases", "purchase", "purchase_register"):
            return SeriesReportService.generate_purchase_report(
                db=db,
                company_id=company_id,
                vendor_id=vendor_id,
                date_from=date_from,
                date_to=date_to,
                file_format=file_format
            )
        elif rt in ("amazon_returns", "amazon-returns", "amazon_return"):
            return SeriesReportService.generate_amazon_returns_report(
                db=db,
                company_id=company_id,
                date_from=date_from,
                date_to=date_to,
                file_format=file_format
            )
        elif rt in ("sales_returns", "sales-returns", "pos_returns", "returns"):
            return SeriesReportService.generate_sales_returns_report(
                db=db,
                company_id=company_id,
                date_from=date_from,
                date_to=date_to,
                file_format=file_format
            )
        else:
            return SeriesReportService.generate_series_sales_report(
                db=db,
                company_id=company_id,
                series=series,
                date_from=date_from,
                date_to=date_to,
                file_format=file_format
            )
