import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schema import Company, CompanySettings, Product, Warehouse, Inventory, Sale, SaleItem, User
from app.services.einvoice.payload_builder import build_einvoice_payload
from app.services.einvoice.irp_client import IRPClient
from app.services.einvoice.einvoice_service import EInvoiceService

@pytest.fixture
def client():
    return TestClient(app)

def test_einvoice_payload_and_simulation(db_session):
    # 1. Setup Company & Settings
    company = Company(name="B K RAMAN AND CO", code="BKR")
    db_session.add(company)
    db_session.flush()

    settings = CompanySettings(
        company_id=company.id,
        legal_name="B K RAMAN AND CO",
        gstin="04AEFPS6301F1ZU",
        address="Plot No. 150, Industrial Area Phase 1",
        state="Chandigarh",
        state_code="04",
        einvoice_enabled=True,
        einvoice_provider="SANDBOX"
    )
    db_session.add(settings)

    # 2. Setup Warehouse & Product
    wh = Warehouse(company_id=company.id, name="BKR Central Godown", code="BKR-WH", address="Plot 150 Industrial Area")
    db_session.add(wh)

    prod = Product(
        company_id=company.id,
        sku="LG0831",
        name="Angle Grinder 800W",
        hsn="84672100",
        item_rate=2500.0,
        default_gst_rate=18.0
    )
    db_session.add(prod)
    db_session.flush()

    # 3. Create B2B Sale
    sale = Sale(
        company_id=company.id,
        bill_number="BILL-EINV-001",
        invoice_number="INV-2026-001",
        invoice_type="B2B",
        customer_name="Punjab Machinery Store",
        customer_gstin="03ABCDE1234F1Z5",
        customer_address="Shop 12, GT Road, Ludhiana",
        customer_state="Punjab",
        customer_state_code="03",
        place_of_supply="03",
        company_gstin_snapshot="04AEFPS6301F1ZU",
        company_name_snapshot="B K RAMAN AND CO",
        company_address_snapshot="Plot No. 150, Industrial Area Phase 1",
        company_state_snapshot="Chandigarh",
        company_state_code_snapshot="04",
        grand_total=2950.0,
        total_taxable_amount=2500.0,
        total_tax=450.0
    )
    db_session.add(sale)
    db_session.flush()

    item = SaleItem(
        sale_id=sale.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        hsn_sac=prod.hsn,
        quantity=1,
        selling_price=2500.0,
        taxable_amount=2500.0,
        gst_rate=18.0,
        igst=450.0,
        cgst=0.0,
        sgst=0.0,
        line_total=2950.0
    )
    db_session.add(item)
    db_session.commit()

    # 4. Test Payload Builder
    payload = build_einvoice_payload(sale, db=db_session)
    assert payload["Version"] == "1.1"
    assert payload["DocDtls"]["No"] == "INV-2026-001"
    assert payload["SellerDtls"]["Gstin"] == "04AEFPS6301F1ZU"
    assert payload["BuyerDtls"]["Gstin"] == "03ABCDE1234F1Z5"
    assert len(payload["ItemList"]) == 1
    assert payload["ItemList"][0]["HsnCd"] == "84672100"
    assert payload["ValDtls"]["TotInvVal"] == 2950.0

    # 5. Test IRPClient in Sandbox Mode
    client = IRPClient(provider="SANDBOX")
    res = client.generate_irn(payload)
    assert res["success"] is True
    assert len(res["irn"]) == 64
    assert res["ack_no"] is not None
    assert "qr_code_data" in res

    # 6. Test EInvoiceService orchestration & DB persistence
    service_res = EInvoiceService.generate_irn_for_sale(sale_id=sale.id, db=db_session)
    assert service_res["status"] == "SUCCESS"
    assert len(service_res["irn"]) == 64

    # Verify Sale was updated in DB
    db_session.refresh(sale)
    assert sale.einvoice_status == "GENERATED"
    assert sale.einvoice_irn == service_res["irn"]
    assert sale.einvoice_ack_no is not None
    assert sale.einvoice_qr_code_data is not None

    # 7. Test EInvoice Cancellation
    cancel_res = EInvoiceService.cancel_irn_for_sale(
        sale_id=sale.id,
        cancel_reason="2",
        remarks="Data entry mistake test",
        db=db_session
    )
    assert cancel_res["status"] == "SUCCESS"
    db_session.refresh(sale)
    assert sale.einvoice_status == "CANCELLED"
