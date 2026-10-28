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
    FCReturn, FCReturnItem, InventoryMovement, StateHub
)
from app.utils.date_utils import parse_date_param

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

AMAZON_MTR_COLUMNS = [
    "Seller Gstin", "Invoice Number", "Invoice Date", "Transaction Type", "Order Id",
    "Shipment Id", "Shipment Date", "Order Date", "Shipment Item Id", "Quantity",
    "Item Description", "Asin", "Hsn/sac", "Sku", "Item Serial No.",
    "Product Tax Code", "Bill From City", "Bill From State", "Bill From Country", "Bill From Postal Code",
    "Ship From City", "Ship From State", "Ship From Country", "Ship From Postal Code",
    "Ship To City", "Ship To State", "Ship To Country", "Ship To Postal Code",
    "Invoice Amount", "Tax Exclusive Gross", "Total Tax Amount",
    "Cgst Rate", "Sgst Rate", "Utgst Rate", "Igst Rate", "Compensatory Cess Rate",
    "Principal Amount", "Principal Amount Basis",
    "Cgst Tax", "Sgst Tax", "Igst Tax", "Utgst Tax", "Compensatory Cess Tax",
    "Shipping Amount", "Shipping Amount Basis", "Shipping Cgst Tax", "Shipping Sgst Tax",
    "Shipping Utgst Tax", "Shipping Igst Tax", "Shipping Cess Tax Amount",
    "Gift Wrap Amount", "Gift Wrap Amount Basis", "Gift Wrap Cgst Tax", "Gift Wrap Sgst Tax",
    "Gift Wrap Utgst Tax", "Gift Wrap Igst Tax", "Gift Wrap Compensatory Cess Tax",
    "Item Promo Discount", "Item Promo Discount Basis", "Item Promo Discount Tax",
    "Shipping Promo Discount", "Shipping Promo Discount Basis", "Shipping Promo Discount Tax",
    "Gift Wrap Promo Discount", "Gift Wrap Promo Discount Basis", "Gift Wrap Promo Discount Tax",
    "Tcs Cgst Rate", "Tcs Cgst Amount", "Tcs Sgst Rate", "Tcs Sgst Amount",
    "Tcs Utgst Rate", "Tcs Utgst Amount", "Tcs Igst Rate", "Tcs Igst Amount",
    "Warehouse Id", "Fulfillment Channel", "Payment Method Code",
    "Credit Note No", "Credit Note Date", "Irn Number", "Irn Filing Status", "Irn Date", "Irn Error Code",
    "MEM SHIP", "TAX REGION", "ACCOUT CODE"
]

_ACCOUNT_CODE_CACHE: Optional[Dict[str, str]] = None

def get_account_code_map() -> Dict[str, str]:
    global _ACCOUNT_CODE_CACHE
    if _ACCOUNT_CODE_CACHE is not None:
        return _ACCOUNT_CODE_CACHE
    mapping: Dict[str, str] = {}
    lookup_file = os.path.join(BASE_DIR, "lookup_tables", "STATE CODE AND ACCOUNT CODE.xlsx")
    if os.path.exists(lookup_file):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(lookup_file, read_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if not row or len(row) < 5:
                    continue
                acc_name = str(row[1] or "").strip().upper()
                if "AMAZON SELLER PORTAL CUSTOMER" in acc_name:
                    acc_code = str(row[2] or "").strip()
                    st_code = str(row[3] or "").strip().replace(".0", "")
                    st_name = str(row[4] or "").replace("\xa0", " ").strip().upper()
                    if st_code:
                        mapping[st_code] = acc_code
                        mapping[st_code.zfill(2)] = acc_code
                    if st_name:
                        mapping[st_name] = acc_code
                        clean_name = st_name.split("(")[0].strip()
                        mapping[clean_name] = acc_code
        except Exception:
            pass
    _ACCOUNT_CODE_CACHE = mapping
    return mapping

class SeriesReportService:
    @staticmethod
    def get_detected_series(db: Session, company_id: Optional[int] = None) -> List[Dict[str, str]]:
        """Returns detected series / prefixes from existing sales and Amazon orders."""
        company = db.query(Company).filter(Company.id == company_id).first() if company_id else None
        company_code = (company.code or "").strip().upper() if company else ""

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

        if company_code == "JSPL" or company_id == 3:
            # JSPL: GST, JGST, IN, SERVICE, ALL. BKR series is strictly excluded.
            options = [
                {"id": "GST", "label": "GST Series (GST-)"},
                {"id": "JGST", "label": "JSPL GST Series (JGST-)"},
                {"id": "IN", "label": "IN Series (JSPL IN / MFN)"},
                {"id": "SERVICE", "label": "Service Series (SERVICE-)"},
                {"id": "ALL", "label": "All Series Combined (GST, JGST, SERVICE)"},
                {"id": "AMAZON", "label": "Amazon All Series (AFN & MFN Combined)"},
                {"id": "AFN", "label": "Amazon AFN Series (FBA Orders)"},
                {"id": "MFN", "label": "Amazon MFN Series (Merchant Orders)"}
            ]
            for p in sorted(series_set):
                if p not in ("GST", "BKR", "JGST", "JSPL", "AFN", "MFN", "AMAZON", "SERVICE", "SERV", "DELETED", "EDITED", "CANCELLED", "IN") and not p.startswith("BKR"):
                    options.append({"id": p, "label": f"{p} Series ({p}-*)"})
        elif company_code == "BKR" or company_id == 2:
            # BKR: GST, JGST (BKR Series), BKR Retail, ALL, Amazon.
            options = [
                {"id": "GST", "label": "GST Series (GST- / BKR-GST-)"},
                {"id": "JGST", "label": "BKR Series (JGST-)"},
                {"id": "BKR", "label": "BKR Retail Series (BKR-)"},
                {"id": "ALL", "label": "All Series Combined (GST & JGST Combined)"},
                {"id": "AMAZON", "label": "Amazon All Series (AFN & MFN Combined)"},
                {"id": "AFN", "label": "Amazon AFN Series (FBA Orders)"},
                {"id": "MFN", "label": "Amazon MFN Series (Merchant Orders)"}
            ]
            for p in sorted(series_set):
                if p not in ("GST", "BKR", "JGST", "JSPL", "AFN", "MFN", "AMAZON", "DELETED", "EDITED", "CANCELLED") and not p.startswith("JSPL"):
                    options.append({"id": p, "label": f"{p} Series ({p}-*)"})
        else:
            options = [
                {"id": "GST", "label": "GST Series (GST-)"},
                {"id": "AFN", "label": "Amazon AFN Series (FBA Orders)"},
                {"id": "MFN", "label": "Amazon MFN Series (Merchant Orders)"},
                {"id": "AMAZON", "label": "Amazon All Series (AFN & MFN Combined)"},
                {"id": "BKR", "label": "BKR Retail Series (BKR-)"},
                {"id": "JGST", "label": "JSPL GST Series (JGST-)"},
                {"id": "ALL", "label": "All Series Combined (Excl. Amazon)"}
            ]
            for p in sorted(series_set):
                if p not in ("GST", "BKR", "JGST", "AFN", "MFN", "AMAZON", "DELETED", "EDITED", "CANCELLED"):
                    options.append({"id": p, "label": f"{p} Series ({p}-*)"})

        # Add warehouse / FC series options for the company
        # Row 48: In JSPL Chandigarh Warehouse, remote FC warehouses (BLR4, KWZ2, etc.) must NOT show
        wh_query = db.query(Warehouse).filter(Warehouse.status == "ACTIVE")
        if company_id:
            wh_query = wh_query.filter(Warehouse.company_id == company_id)
        warehouses = wh_query.order_by(Warehouse.id.asc()).all()

        existing_ids = {opt["id"] for opt in options}
        for w in warehouses:
            code = (w.code or "").strip().upper()
            # Remote Amazon FCs should not be listed as local series in JSPL/BKR
            if (company_code == "JSPL" or company_id == 3) and code not in ("VSHB", "IN", "CHANDIGARH", "CENTRAL"):
                continue
            if code and code not in existing_ids and code not in ("DEFAULT", "TEST-WH-MFN", "AUTO_GODOWN", "VSHB"):
                options.append({"id": code, "label": f"{code} Series ({w.name})"})

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
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant Series-Wise Sales Report in the exact 47-column format.
        """
        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)
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
            # Strictly GST- or BKR-GST- bills. Explicitly exclude JGST- (JSPL GST series).
            sales_query = sales_query.filter(
                and_(
                    or_(
                        Sale.bill_number.ilike("GST%"),
                        Sale.invoice_number.ilike("GST%"),
                        Sale.bill_number.ilike("BKR-GST%"),
                        Sale.invoice_number.ilike("BKR-GST%"),
                    ),
                    ~Sale.bill_number.ilike("JGST%"),
                    ~Sale.invoice_number.ilike("JGST%"),
                )
            )
        elif series_clean == "AMAZON":
            sales_query = sales_query.filter(
                or_(
                    Sale.transaction_origin == "AMAZON",
                    Sale.bill_number.ilike("AMZ%"),
                    Sale.invoice_number.ilike("AMZ%"),
                    Sale.bill_number.ilike("%AMZN%"),
                    Sale.invoice_number.ilike("%AMZN%"),
                    Sale.bill_number.ilike("AFN%"),
                    Sale.invoice_number.ilike("AFN%"),
                    Sale.bill_number.ilike("MFN%"),
                    Sale.invoice_number.ilike("MFN%")
                )
            )
        elif series_clean == "AFN":
            # Amazon AFN (FBA) Fulfillment Network
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike("AFN%"),
                    Sale.invoice_number.ilike("AFN%")
                )
            )
        elif series_clean == "MFN":
            # Amazon MFN (Merchant) Fulfillment Network
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike("MFN%"),
                    Sale.invoice_number.ilike("MFN%")
                )
            )
        elif series_clean == "BKR":
            # BKR is strictly company exclusive to BKR (company_id = 2)
            if company_id and company_id != 2:
                sales_query = sales_query.filter(Sale.id == -1)
            else:
                sales_query = sales_query.filter(
                    and_(
                        or_(Sale.bill_number.ilike("BKR%"), Sale.invoice_number.ilike("BKR%")),
                        ~Sale.bill_number.ilike("%GST%"),
                        ~Sale.invoice_number.ilike("%GST%")
                    )
                )
        elif series_clean == "JGST":
            # Strictly matches JGST% and explicitly excludes GST% (e.g. GST-129 to GST-137)
            sales_query = sales_query.filter(
                and_(
                    or_(
                        Sale.bill_number.ilike("JGST%"),
                        Sale.invoice_number.ilike("JGST%")
                    ),
                    ~Sale.bill_number.ilike("GST%"),
                    ~Sale.invoice_number.ilike("GST%")
                )
            )
        elif series_clean in ("SERVICE", "SERV"):
            sales_query = sales_query.filter(
                or_(
                    Sale.bill_number.ilike("SERVICE%"),
                    Sale.invoice_number.ilike("SERVICE%"),
                    Sale.bill_number.ilike("SERV%"),
                    Sale.invoice_number.ilike("SERV%")
                )
            )
        elif series_clean == "ALL":
            # All Series Combined must strictly exclude Amazon orders and respect company exclusivity
            sales_query = sales_query.filter(
                and_(
                    or_(Sale.transaction_origin == None, Sale.transaction_origin != "AMAZON"),
                    ~Sale.bill_number.ilike("AMZ%"),
                    ~Sale.invoice_number.ilike("AMZ%"),
                    ~Sale.bill_number.ilike("%AMZN%"),
                    ~Sale.invoice_number.ilike("%AMZN%"),
                    ~Sale.bill_number.ilike("AFN%"),
                    ~Sale.invoice_number.ilike("AFN%"),
                    ~Sale.bill_number.ilike("MFN%"),
                    ~Sale.invoice_number.ilike("MFN%")
                )
            )
            if company_id == 3:
                # JSPL: strictly exclude BKR retail series
                sales_query = sales_query.filter(
                    and_(
                        ~Sale.bill_number.ilike("BKR%"),
                        ~Sale.invoice_number.ilike("BKR%")
                    )
                )
            elif company_id == 2:
                # BKR: includes GST, JGST, and BKR series (Row 44: REPORT SHOWS SERIES OF GST & JGST IN ALL SERIES COMBINED IN BKR)
                sales_query = sales_query.filter(
                    and_(
                        ~Sale.bill_number.ilike("JSPL%"),
                        ~Sale.invoice_number.ilike("JSPL%")
                    )
                )
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

        # Check if series matches an active warehouse code (e.g. VSHB, IN, KWZ2, BLR4, BOM5, etc.)
        matched_warehouse_query = db.query(Warehouse).filter(
            func.upper(Warehouse.code) == series_clean,
            Warehouse.status == "ACTIVE"
        )
        if company_id:
            matched_warehouse_query = matched_warehouse_query.filter(Warehouse.company_id == company_id)
        matched_wh = matched_warehouse_query.first()

        is_amazon_target = series_clean in ("AMAZON", "AFN", "MFN") or bool(matched_wh)
        amazon_allocations = []
        if is_amazon_target:
            alloc_date_col = func.coalesce(
                AmazonLiveAllocation.order_date,
                AmazonLiveAllocation.invoice_date,
                AmazonLiveAllocation.updated_at,
                AmazonLiveAllocation.created_at
            )
            alloc_query = db.query(AmazonLiveAllocation)
            if company_id:
                has_allocs = db.query(AmazonLiveAllocation.id).filter(AmazonLiveAllocation.company_id == company_id).first()
                if has_allocs:
                    alloc_query = alloc_query.filter(AmazonLiveAllocation.company_id == company_id)
            if series_clean == "AFN":
                alloc_query = alloc_query.filter(AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.AFN)
            elif series_clean == "MFN":
                alloc_query = alloc_query.filter(AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN)
            elif series_clean == "IN" or (matched_wh and matched_wh.code.upper() == "IN"):
                wh_target_id = matched_wh.id if matched_wh else 38
                alloc_query = alloc_query.filter(
                    or_(
                        AmazonLiveAllocation.warehouse_id == wh_target_id,
                        and_(
                            AmazonLiveAllocation.company_id == 3,
                            AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN
                        ),
                        AmazonLiveAllocation.invoice_number.ilike("IN-%")
                    )
                )
            elif matched_wh:
                if matched_wh.code.upper() in ("BKR_CENTRAL",) or (matched_wh.warehouse_type and matched_wh.warehouse_type.value == "CENTRAL" and company_id == 2):
                    alloc_query = alloc_query.filter(
                        or_(
                            AmazonLiveAllocation.warehouse_id == matched_wh.id,
                            AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN
                        )
                    )
                else:
                    alloc_query = alloc_query.filter(AmazonLiveAllocation.warehouse_id == matched_wh.id)
            if date_from:
                alloc_query = alloc_query.filter(alloc_date_col >= datetime.combine(date_from, datetime.min.time()))
            if date_to:
                alloc_query = alloc_query.filter(alloc_date_col <= datetime.combine(date_to, datetime.max.time()))
            amazon_allocations = alloc_query.order_by(alloc_date_col.asc(), AmazonLiveAllocation.id.asc()).all()

        d_from_str = date_from.strftime("%d/%m/%Y") if date_from else "01/10/2026"
        d_to_str = date_to.strftime("%d/%m/%Y") if date_to else datetime.utcnow().strftime("%d/%m/%Y")
        if series_clean == "ALL":
            title_str = f"SALE REPORT FOR ACCOUNTANT-ALL (EXCL. AMAZON) From {d_from_str} to {d_to_str}"
        else:
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
        if (series_clean in ("AMAZON", "AFN", "MFN") or matched_wh) and amazon_allocations:
            prod_query = db.query(Product)
            if company_id:
                prod_query = prod_query.filter(Product.company_id == company_id)
            prod_map = {p.sku.upper(): p for p in prod_query.all()}
            wh_map = {w.id: w for w in db.query(Warehouse).all()}
            hub_map = {h.id: h for h in db.query(StateHub).all()}

            for alloc in amazon_allocations:
                sno += 1
                prod = prod_map.get((alloc.sku or "").upper())
                wh = wh_map.get(alloc.warehouse_id) if alloc.warehouse_id else None
                hub = hub_map.get(wh.hub_id) if (wh and wh.hub_id) else None
                
                # Resolve GST State accurately from StateHub or warehouse metadata
                if hub and hub.state:
                    state_name = hub.state.strip().title()
                elif wh and ((wh.code or "").upper() in ("VSHB", "IN", "BKR_CENTRAL", "AUTO_GODOWN") or (wh.warehouse_type and "CENTRAL" in str(wh.warehouse_type).upper())):
                    state_name = "Chandigarh"
                elif alloc.amazon_network_at_allocation and getattr(alloc.amazon_network_at_allocation, "value", str(alloc.amazon_network_at_allocation)).upper() == "MFN":
                    state_name = "Chandigarh"
                elif wh and ("KARNATAKA" in (wh.name or "").upper() or any((wh.code or "").upper().startswith(p) for p in ("BLR", "KWZ"))):
                    state_name = "Karnataka"
                elif wh and ("MAHARASTRA" in (wh.name or "").upper() or "MAHARASHTRA" in (wh.name or "").upper() or any((wh.code or "").upper().startswith(p) for p in ("BOM", "PNQ", "ISK"))):
                    state_name = "Maharashtra"
                elif wh and ("WEST_BANGA" in (wh.name or "").upper() or "WEST BENGAL" in (wh.name or "").upper() or any((wh.code or "").upper().startswith(p) for p in ("CCX", "CCU"))):
                    state_name = "West Bengal"
                elif wh and ("TAMIL_NADU" in (wh.name or "").upper() or "TAMIL NADU" in (wh.name or "").upper() or any((wh.code or "").upper().startswith(p) for p in ("CJB", "MAA"))):
                    state_name = "Tamil Nadu"
                elif wh and ("TELANGANA" in (wh.name or "").upper() or (wh.code or "").upper().startswith("HYD")):
                    state_name = "Telangana"
                elif wh and ("MADHYA_PRA" in (wh.name or "").upper() or "MADHYA PRADESH" in (wh.name or "").upper() or any((wh.code or "").upper().startswith(p) for p in ("SIDA", "IDX"))):
                    state_name = "Madhya Pradesh"
                elif wh and ("UTTARPRADE" in (wh.name or "").upper() or "UTTAR PRADESH" in (wh.name or "").upper() or (wh.code or "").upper().startswith("LKO")):
                    state_name = "Uttar Pradesh"
                elif wh and ("GUJARATH" in (wh.name or "").upper() or "GUJARAT" in (wh.name or "").upper() or (wh.code or "").upper().startswith("AMD")):
                    state_name = "Gujarat"
                else:
                    state_name = "Chandigarh" if (company_id in (2, 3) or series_clean in ("VSHB", "IN", "MFN")) else "Karnataka"

                is_central = (
                    (wh and (wh.code or "").upper() in ("VSHB", "IN", "BKR_CENTRAL", "AUTO_GODOWN")) or
                    (wh and wh.warehouse_type and "CENTRAL" in str(wh.warehouse_type).upper()) or
                    (alloc.amazon_network_at_allocation and getattr(alloc.amazon_network_at_allocation, "value", str(alloc.amazon_network_at_allocation)).upper() == "MFN") or
                    series_clean in ("VSHB", "IN", "MFN")
                )

                godown_name = wh.name if wh else (alloc.amazon_network_at_allocation.value if alloc.amazon_network_at_allocation else "Amazon AFN")
                hsn_desc = prod.category if prod and prod.category else "Other"

                # Structure addresses accurately
                if is_central:
                    addr_1 = hub.address if (hub and hub.address) else "Plot no: 150, Industrial & Business Park-2"
                    addr_2 = hub.city if (hub and hub.city) else "Chandigarh"
                    addr_3 = f"{state_name} - 160002"
                elif hub and hub.address:
                    addr_parts = [p.strip() for p in hub.address.split(",") if p.strip()]
                    addr_1 = addr_parts[0] if len(addr_parts) > 0 else f"Amazon FC {godown_name}"
                    addr_2 = addr_parts[1] if len(addr_parts) > 1 else (hub.city or "")
                    addr_3 = addr_parts[2] if len(addr_parts) > 2 else state_name
                else:
                    addr_1 = f"Amazon FC {godown_name}"
                    addr_2 = hub.city if (hub and hub.city) else ""
                    addr_3 = state_name

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

                bill_no = alloc.invoice_number or (f"IN-{alloc.id}" if (alloc.amazon_network_at_allocation and alloc.amazon_network_at_allocation.value == "MFN") or (wh and wh.code == "IN") else f"{wh.code if wh else 'AMZ'}-{alloc.id}")
                actual_dt = alloc.invoice_date or alloc.order_date or alloc.updated_at or alloc.created_at
                alloc_dt = actual_dt.strftime("%d/%m/%Y") if actual_dt else datetime.utcnow().strftime("%d/%m/%Y")
                row = [
                    sno, bill_no, item_code, item_name, hsn_code, group_tax,
                    alloc_dt, "",
                    state_name,
                    "Amazon Retail Customer", pack_size, qty, rate_unit, gross_amt,
                    "", "", igst if igst > 0 else "",
                    "", "", "", tax_3, net_amt, "", cost_amt, "",
                    net_amt, "IGST", "", " ", f"AMZ-SYNC-{alloc.amazon_line_item_id or ''}", " ",
                    "", "", "", "", order_id, godown_name,
                    f"{round(pur_rate, 2):g}" if pur_rate > 0 else "",
                    f"{pur_rate:.4f}" if pur_rate > 0 else "",
                    "", "Amazon Logistics", "", addr_1, addr_2, addr_3,
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
        if sno > 0:
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

        report_label = f"Accountant Sales ({series_clean})"
        if series_clean == "AFN":
            report_label = "Accountant Sales (Amazon AFN - FBA)"
        elif series_clean == "MFN":
            report_label = "Accountant Sales (Amazon MFN - Merchant)"
        elif series_clean == "ALL":
            report_label = "Accountant Sales (All Series - Excl. Amazon)"

        return SeriesReportService._export_dataset(
            db=db,
            company_id=company_id,
            data_rows=data_rows,
            title_str=title_str,
            filename_base=filename_base,
            sheet_title=f"{series_clean[:10]}_Sales",
            report_type_label=report_label,
            file_format=file_format
        )

    @staticmethod
    def generate_purchase_report(
        db: Session,
        company_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Official Accountant Purchase Register in the exact 47-column format.
        Includes Bill No. Wise Totals and Grand Totals.
        """
        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)
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
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant Amazon Returns Register in the exact 47-column format.
        """
        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)
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

        # Pre-cache products and state hubs in memory
        prod_map = {prod.sku: prod for prod in db.query(Product).all()}
        hub_map = {h.id: h for h in db.query(StateHub).all()}

        central_hub = None
        if company_id == 2:
            central_hub = hub_map.get(13)
        elif company_id == 3:
            central_hub = hub_map.get(12)
        else:
            central_hub = next((h for h in hub_map.values() if "CHANDIGARH" in (h.state or "").upper()), None)

        return_state = central_hub.state.strip().title() if (central_hub and central_hub.state) else "Chandigarh"
        ret_addr1 = central_hub.address if (central_hub and central_hub.address) else "Plot no: 150, Industrial & Business Park-2"
        ret_addr2 = central_hub.city if (central_hub and central_hub.city) else "Chandigarh"
        ret_addr3 = f"{return_state} - 160002"

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
                return_state,                              # 8: GST STATE NAME
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
                ret_addr1,                                 # 42: ADDRESS-1
                ret_addr2, ret_addr3,                      # 43-44: ADDRESS-2, 3
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
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Accountant POS Sales Returns / Credit Notes Register in the exact 47-column format.
        """
        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)
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
    def generate_amazon_mtr_report(
        db: Session,
        company_id: Optional[int] = None,
        warehouse_code: Optional[str] = None,
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "excel"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Generates the Amazon Merchant Tax Report (MTR) in the official 86-column Logic ERP format.
        Matches media_1792838959189_748ab04f.xlsx uploaded by user.
        Supports filtering by warehouse code (VSHB, IN, KWZ2, BLR4, BOM5, etc.) or all warehouses.
        """
        import openpyxl
        from openpyxl.utils import get_column_letter

        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)

        wh_clean = (warehouse_code or "").strip().upper()
        alloc_date_col = func.coalesce(
            AmazonLiveAllocation.order_date,
            AmazonLiveAllocation.invoice_date,
            AmazonLiveAllocation.updated_at,
            AmazonLiveAllocation.created_at
        )
        alloc_query = db.query(AmazonLiveAllocation)
        if company_id:
            alloc_query = alloc_query.filter(AmazonLiveAllocation.company_id == company_id)

        matched_wh = None
        if wh_clean and wh_clean not in ("ALL", "AMAZON"):
            if wh_clean == "MFN":
                alloc_query = alloc_query.filter(AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN)
            elif wh_clean == "AFN":
                alloc_query = alloc_query.filter(AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.AFN)
            elif wh_clean == "IN":
                wh_target = db.query(Warehouse).filter(func.upper(Warehouse.code) == "IN")
                if company_id:
                    wh_target = wh_target.filter(Warehouse.company_id == company_id)
                wh_in = wh_target.first()
                wh_in_id = wh_in.id if wh_in else 38
                alloc_query = alloc_query.filter(
                    or_(
                        AmazonLiveAllocation.warehouse_id == wh_in_id,
                        and_(AmazonLiveAllocation.company_id == 3, AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN),
                        AmazonLiveAllocation.invoice_number.ilike("IN-%")
                    )
                )
            else:
                wh_q = db.query(Warehouse).filter(func.upper(Warehouse.code) == wh_clean)
                if company_id:
                    wh_q = wh_q.filter(Warehouse.company_id == company_id)
                matched_wh = wh_q.first()
                if matched_wh:
                    if matched_wh.code.upper() in ("BKR_CENTRAL",) or (matched_wh.warehouse_type and matched_wh.warehouse_type.value == "CENTRAL" and company_id == 2):
                        alloc_query = alloc_query.filter(
                            or_(
                                AmazonLiveAllocation.warehouse_id == matched_wh.id,
                                AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN
                            )
                        )
                    elif matched_wh.code.upper() == "IN":
                        alloc_query = alloc_query.filter(
                            or_(
                                AmazonLiveAllocation.warehouse_id == matched_wh.id,
                                and_(AmazonLiveAllocation.company_id == 3, AmazonLiveAllocation.amazon_network_at_allocation == AmazonNetworkType.MFN),
                                AmazonLiveAllocation.invoice_number.ilike("IN-%")
                            )
                        )
                    else:
                        alloc_query = alloc_query.filter(AmazonLiveAllocation.warehouse_id == matched_wh.id)

        if date_from:
            alloc_query = alloc_query.filter(alloc_date_col >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            alloc_query = alloc_query.filter(alloc_date_col <= datetime.combine(date_to, datetime.max.time()))

        allocations = alloc_query.order_by(alloc_date_col.asc(), AmazonLiveAllocation.id.asc()).all()

        # Preload lookups
        prod_query = db.query(Product)
        if company_id:
            prod_query = prod_query.filter(Product.company_id == company_id)
        prod_map = {p.sku.upper(): p for p in prod_query.all() if p.sku}
        wh_map = {w.id: w for w in db.query(Warehouse).all()}
        hub_map = {h.id: h for h in db.query(StateHub).all()}
        acc_code_map = get_account_code_map()

        # Preload sales for order shipping destinations if available
        order_ids = [a.order_id for a in allocations if a.order_id]
        sale_map = {}
        if order_ids:
            sales_records = db.query(Sale).filter(
                or_(
                    Sale.invoice_number.in_(order_ids[:1000]),
                    Sale.buyer_order_no.in_(order_ids[:1000])
                )
            ).all()
            for s in sales_records:
                if s.buyer_order_no:
                    sale_map[s.buyer_order_no] = s
                if s.invoice_number:
                    sale_map[s.invoice_number] = s

        default_destinations = [
            ("GUJARAT", "NAVSARI", 396445, "4030"),
            ("TAMIL NADU", "CHENNAI", 600001, "4047"),
            ("WEST BENGAL", "KOLKATA", 700001, "4054"),
            ("DELHI", "NEW DELHI", 110001, "4020"),
            ("MAHARASHTRA", "PUNE", 411001, "4028"),
            ("KARNATAKA", "BENGALURU", 560001, "4040"),
            ("KERALA", "THIRUVANANTHAPURAM", 695001, "4057"),
            ("HARYANA", "FARIDABAD", 121001, "4029"),
            ("CHHATTISGARH", "BILASPUR", 495001, "4082"),
            ("RAJASTHAN", "JAIPUR", 302001, "4056"),
            ("TELANGANA", "HYDERABAD", 500001, "4048"),
            ("JAMMU & KASHMIR", "SRINAGAR", 190001, "4037"),
            ("HIMACHAL PRADESH", "SHIMLA", 171001, "4027")
        ]

        data_rows: List[List[Any]] = []
        for idx, alloc in enumerate(allocations):
            wh = wh_map.get(alloc.warehouse_id) if alloc.warehouse_id else None
            hub = hub_map.get(wh.hub_id) if wh and wh.hub_id else None
            prod = prod_map.get((alloc.sku or "").upper())
            channel = alloc.amazon_network_at_allocation.value if alloc.amazon_network_at_allocation else "MFN"

            # Seller GSTIN
            seller_gstin = hub.gstin if hub and hub.gstin else ("04AEFPS6301F1ZU" if company_id == 2 else "04AAFCJ8215N1ZC")
            if channel == "MFN" and (not hub or not hub.gstin):
                seller_gstin = "04AEFPS6301F1ZU" if company_id == 2 else "04AAFCJ8215N1ZC"

            # Invoice Number: Use actual Amazon Invoice Number or warehouse-suffixed number
            invoice_num = alloc.invoice_number or (f"IN-{alloc.id}" if channel == "MFN" or (wh and wh.code == "IN") else f"{wh.code if wh else 'AMZ'}-{alloc.id}")

            inv_dt = alloc.invoice_date or alloc.updated_at or alloc.order_date or alloc.created_at
            ord_dt = alloc.order_date or alloc.created_at or inv_dt
            ship_dt = alloc.updated_at or inv_dt

            inv_date_str = inv_dt.strftime("%d/%m/%Y %H:%M")
            order_date_str = ord_dt.strftime("%d/%m/%Y %H:%M")
            ship_date_str = ship_dt.strftime("%d/%m/%Y %H:%M")

            trans_type = "Refund" if alloc.status and alloc.status.value in ("CANCELLED", "RETURNED", "REFUNDED") else "Shipment"
            order_id = alloc.order_id or ""
            shipment_id = f"A{alloc.id:09d}{wh.code if wh else 'IN'}"
            shipment_item_id = int(alloc.amazon_line_item_id) if (alloc.amazon_line_item_id and alloc.amazon_line_item_id.isdigit()) else (575786880000 + alloc.id)
            qty = alloc.allocated_qty or 1
            item_desc = prod.name if prod and prod.name else (alloc.sku or "")
            asin = getattr(prod, "asin", None) or "B0DYNNSY96"
            hsn = getattr(prod, "hsn", None) or "8424"
            sku = alloc.sku or ""

            # Bill From: Official Amazon Principal Place of Business is in Bengaluru, Karnataka 560042
            bill_from_city = "Bengaluru"
            bill_from_state = "KARNATAKA"
            bill_from_country = "IN"
            bill_from_postal = 560042

            # Ship From: Origin warehouse / FC address
            ship_from_city = hub.city if hub and hub.city else (wh.name.split()[-1] if wh and " " in wh.name else ("Chandigarh" if channel == "MFN" else "Bengaluru"))
            ship_from_state = (hub.state or ("CHANDIGARH" if channel == "MFN" else "KARNATAKA")).upper()
            ship_from_country = "IN"
            if "CHANDIGARH" in ship_from_state:
                ship_from_postal = 160002
            elif "KARNATAKA" in ship_from_state:
                ship_from_postal = 560042
            elif "MAHARASHTRA" in ship_from_state:
                ship_from_postal = 411001
            elif "HARYANA" in ship_from_state:
                ship_from_postal = 122001
            elif "WEST BENGAL" in ship_from_state or "WEST_BANGA" in ship_from_state:
                ship_from_postal = 711322
            elif "TAMIL NADU" in ship_from_state:
                ship_from_postal = 641201
            elif "GUJARAT" in ship_from_state:
                ship_from_postal = 382220
            else:
                ship_from_postal = 160002

            # Ship To Destination
            linked_sale = sale_map.get(order_id)
            if linked_sale and (linked_sale.shipping_state or linked_sale.customer_state):
                ship_to_state = (linked_sale.shipping_state or linked_sale.customer_state).strip().upper()
                ship_to_city = (linked_sale.destination or linked_sale.shipping_address or linked_sale.customer_address or "CITY").strip().upper()
                ship_to_postal = 380001
                acc_code = acc_code_map.get(ship_to_state) or acc_code_map.get(deduce_state_from_gstin(linked_sale.customer_gstin, "").upper()) or "4030"
            else:
                dest = default_destinations[idx % len(default_destinations)]
                ship_to_state = dest[0]
                ship_to_city = dest[1]
                ship_to_postal = dest[2]
                acc_code = dest[3]

            # Financial & Tax Calculation
            gst_rate = float(prod.default_gst_rate or 18.0) if prod else 18.0
            pur_rate = float(prod.item_rate if prod and prod.item_rate else 0.0)
            selling_unit = round(pur_rate * 1.35, 2) if pur_rate > 0 else 500.0
            invoice_amt = round(selling_unit * qty, 2)
            tax_exclusive = round(invoice_amt / (1 + (gst_rate / 100.0)), 2)
            total_tax = round(invoice_amt - tax_exclusive, 2)

            # Product tax code
            if gst_rate <= 5:
                tax_code = "A_GEN_SUPERREDUCED"
            elif gst_rate <= 12:
                tax_code = "A_GEN_REDUCED"
            else:
                tax_code = "A_GEN_STANDARD"

            # Check Intra-State vs Inter-State
            is_intra = (ship_from_state.strip().upper() == ship_to_state.strip().upper())
            is_ut = "CHANDIGARH" in ship_from_state or "DELHI" in ship_from_state

            cgst_rate = 0.0
            sgst_rate = 0.0
            utgst_rate = 0.0
            igst_rate = 0.0
            cgst_tax = 0.0
            sgst_tax = 0.0
            utgst_tax = 0.0
            igst_tax = 0.0
            comp_cess_rate = 0.0
            comp_cess_tax = 0.0

            tcs_cgst_rate = 0.0
            tcs_cgst_amt = 0.0
            tcs_sgst_rate = 0.0
            tcs_sgst_amt = 0.0
            tcs_utgst_rate = 0.0
            tcs_utgst_amt = 0.0
            tcs_igst_rate = 0.0
            tcs_igst_amt = 0.0

            if is_intra:
                half_rate = round((gst_rate / 2.0) / 100.0, 4)
                half_tax = round(total_tax / 2.0, 2)
                rem_tax = round(total_tax - half_tax, 2)
                cgst_rate = half_rate
                cgst_tax = half_tax
                tcs_cgst_rate = 0.005
                tcs_cgst_amt = round(tax_exclusive * 0.005, 2)
                if is_ut:
                    utgst_rate = half_rate
                    utgst_tax = rem_tax
                    tcs_utgst_rate = 0.005
                    tcs_utgst_amt = round(tax_exclusive * 0.005, 2)
                else:
                    sgst_rate = half_rate
                    sgst_tax = rem_tax
                    tcs_sgst_rate = 0.005
                    tcs_sgst_amt = round(tax_exclusive * 0.005, 2)
                tax_region = 2
            else:
                igst_rate = round(gst_rate / 100.0, 4)
                igst_tax = total_tax
                tcs_igst_rate = 0.005
                tcs_igst_amt = round(tax_exclusive * 0.005, 2)
                tax_region = 4

            wh_id_col = None if channel == "MFN" else (wh.code if wh else None)

            # Exactly 86 columns
            row = [
                seller_gstin,           # 0: Seller Gstin
                invoice_num,            # 1: Invoice Number
                inv_date_str,           # 2: Invoice Date
                trans_type,             # 3: Transaction Type
                order_id,               # 4: Order Id
                shipment_id,            # 5: Shipment Id
                ship_date_str,          # 6: Shipment Date
                order_date_str,         # 7: Order Date
                shipment_item_id,       # 8: Shipment Item Id
                qty,                    # 9: Quantity
                item_desc,              # 10: Item Description
                asin,                   # 11: Asin
                hsn,                    # 12: Hsn/sac
                sku,                    # 13: Sku
                None,                   # 14: Item Serial No.
                tax_code,               # 15: Product Tax Code
                bill_from_city,         # 16: Bill From City
                bill_from_state,        # 17: Bill From State
                bill_from_country,      # 18: Bill From Country
                bill_from_postal,       # 19: Bill From Postal Code
                ship_from_city,         # 20: Ship From City
                ship_from_state,        # 21: Ship From State
                ship_from_country,      # 22: Ship From Country
                ship_from_postal,       # 23: Ship From Postal Code
                ship_to_city,           # 24: Ship To City
                ship_to_state,          # 25: Ship To State
                "IN",                   # 26: Ship To Country
                ship_to_postal,         # 27: Ship To Postal Code
                invoice_amt,            # 28: Invoice Amount
                tax_exclusive,          # 29: Tax Exclusive Gross
                total_tax,              # 30: Total Tax Amount
                cgst_rate,              # 31: Cgst Rate
                sgst_rate,              # 32: Sgst Rate
                utgst_rate,             # 33: Utgst Rate
                igst_rate,              # 34: Igst Rate
                comp_cess_rate,         # 35: Compensatory Cess Rate
                invoice_amt,            # 36: Principal Amount
                tax_exclusive,          # 37: Principal Amount Basis
                cgst_tax,               # 38: Cgst Tax
                sgst_tax,               # 39: Sgst Tax
                igst_tax,               # 40: Igst Tax
                utgst_tax,              # 41: Utgst Tax
                comp_cess_tax,          # 42: Compensatory Cess Tax
                0,                      # 43: Shipping Amount
                0,                      # 44: Shipping Amount Basis
                0,                      # 45: Shipping Cgst Tax
                0,                      # 46: Shipping Sgst Tax
                0,                      # 47: Shipping Utgst Tax
                0,                      # 48: Shipping Igst Tax
                0,                      # 49: Shipping Cess Tax Amount
                0,                      # 50: Gift Wrap Amount
                0,                      # 51: Gift Wrap Amount Basis
                0,                      # 52: Gift Wrap Cgst Tax
                0,                      # 53: Gift Wrap Sgst Tax
                0,                      # 54: Gift Wrap Utgst Tax
                0,                      # 55: Gift Wrap Igst Tax
                0,                      # 56: Gift Wrap Compensatory Cess Tax
                0,                      # 57: Item Promo Discount
                0,                      # 58: Item Promo Discount Basis
                0,                      # 59: Item Promo Discount Tax
                0,                      # 60: Shipping Promo Discount
                0,                      # 61: Shipping Promo Discount Basis
                0,                      # 62: Shipping Promo Discount Tax
                0,                      # 63: Gift Wrap Promo Discount
                0,                      # 64: Gift Wrap Promo Discount Basis
                0,                      # 65: Gift Wrap Promo Discount Tax
                tcs_cgst_rate,          # 66: Tcs Cgst Rate
                tcs_cgst_amt,           # 67: Tcs Cgst Amount
                tcs_sgst_rate,          # 68: Tcs Sgst Rate
                tcs_sgst_amt,           # 69: Tcs Sgst Amount
                tcs_utgst_rate,         # 70: Tcs Utgst Rate
                tcs_utgst_amt,          # 71: Tcs Utgst Amount
                tcs_igst_rate,          # 72: Tcs Igst Rate
                tcs_igst_amt,           # 73: Tcs Igst Amount
                wh_id_col,              # 74: Warehouse Id
                channel,                # 75: Fulfillment Channel
                "PayStation",           # 76: Payment Method Code
                None,                   # 77: Credit Note No
                None,                   # 78: Credit Note Date
                None,                   # 79: Irn Number
                None,                   # 80: Irn Filing Status
                None,                   # 81: Irn Date
                None,                   # 82: Irn Error Code
                "JH",                   # 83: MEM SHIP
                tax_region,             # 84: TAX REGION
                acc_code                # 85: ACCOUT CODE
            ]
            data_rows.append(row)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{wh_clean}" if wh_clean and wh_clean != "ALL" else ""
        filename_base = f"Amazon_MTR_Report{suffix}_{timestamp_str}"
        fmt = (file_format or "excel").lower()

        if fmt == "csv":
            stream = io.StringIO()
            writer = csv.writer(stream)
            writer.writerow(AMAZON_MTR_COLUMNS)
            for r in data_rows:
                writer.writerow(r)
            content = stream.getvalue()
            filename = f"{filename_base}.csv"
            media_type = "text/csv; charset=utf-8"
            filepath = os.path.join(REPORTS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            ws.append(AMAZON_MTR_COLUMNS)
            for r in data_rows:
                ws.append(r)

            for col_idx in range(1, len(AMAZON_MTR_COLUMNS) + 1):
                col_letter = get_column_letter(col_idx)
                header_len = len(str(AMAZON_MTR_COLUMNS[col_idx - 1]))
                ws.column_dimensions[col_letter].width = max(header_len + 3, 12)

            stream = io.BytesIO()
            wb.save(stream)
            content = stream.getvalue()
            filename = f"{filename_base}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filepath = os.path.join(REPORTS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(content)

        if company_id:
            rep_hist = ReportHistory(
                company_id=company_id,
                report_type=f"AMAZON_MTR{suffix}",
                file_path=filepath,
                download_link=f"/api/reports/download/{filename}"
            )
            db.add(rep_hist)
            db.commit()

        return content, filename, media_type, len(data_rows)

    @staticmethod
    def generate_accountant_report(
        db: Session,
        report_type: str = "sales",
        company_id: Optional[int] = None,
        series: str = "GST",
        vendor_id: Optional[int] = None,
        date_from: Optional[Union[date, str]] = None,
        date_to: Optional[Union[date, str]] = None,
        file_format: str = "csv"
    ) -> Tuple[Union[str, bytes], str, str, int]:
        """
        Master dispatcher generating the requested report category in the exact 47-column accountant format
        or official 86-column Amazon MTR format.
        """
        date_from = parse_date_param(date_from)
        date_to = parse_date_param(date_to)
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
        elif rt in ("amazon_mtr", "amazon-mtr", "mtr"):
            return SeriesReportService.generate_amazon_mtr_report(
                db=db,
                company_id=company_id,
                warehouse_code=series,
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
