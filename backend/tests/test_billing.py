import pytest
from app.models.schema import CompanySettings, Product, Inventory, Warehouse

@pytest.fixture
def setup_billing_data(db_session, seeded_company_context):
    company = seeded_company_context["company"]
    
    # POS requires BKR code
    company.code = "BKR"
    db_session.commit()

    # Create settings
    settings = CompanySettings(
        company_id=company.id,
        tally_enabled=True,
        tally_endpoint_url="http://mocktally:9000",
        tally_payload_format="XML",
        legal_name="BKR Solutions Pvt Ltd",
        gstin="27AAAAA0000A1Z5",
    )
    db_session.add(settings)
    db_session.flush()

    # Create product
    product = Product(
        company_id=company.id,
        sku="TEST-001",
        name="Test Product",
        item_rate=100.0,
        default_gst_rate=18.0,
    )
    db_session.add(product)
    db_session.flush()

    # Create warehouse
    warehouse = Warehouse(company_id=company.id, name="Main Warehouse")
    db_session.add(warehouse)
    db_session.flush()

    # Add inventory
    inv = Inventory(
        company_id=company.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        current_qty=50,
        available_qty=50
    )
    db_session.add(inv)
    db_session.commit()

    return {"company_id": company.id, "product_id": product.id, "sku": "TEST-001"}

def test_company_settings_api(client, setup_billing_data):
    # Get settings
    response = client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert data["tally_enabled"] is True
    assert data["tally_payload_format"] == "XML"
    assert data["legal_name"] == "BKR Solutions Pvt Ltd"

    # Update settings
    payload = {"tally_payload_format": "JSON"}
    response = client.put("/api/settings/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tally_payload_format"] == "JSON"

def test_b2b_pos_checkout_and_tally_sync(client, setup_billing_data):
    # Checkout payload
    payload = {
        "invoice_type": "B2B",
        "customer_name": "Test Client",
        "customer_gstin": "27BBBBB0000B1Z5",
        "customer_state": "Maharashtra",
        "customer_state_code": "27",
        "place_of_supply": "Maharashtra",
        "payment_method": "UPI",
        "payment_reference": "UPI123456",
        "total_taxable_amount": 100.0,
        "total_tax": 18.0,
        "grand_total": 118.0,
        "items": [
            {
                "product_id": setup_billing_data["product_id"],
                "sku": setup_billing_data["sku"],
                "product_name": "Test Product",
                "quantity": 1,
                "selling_price": 100.0,
                "discount": 0.0,
                "gst_rate": 18.0,
                "taxable_amount": 100.0,
                "cgst": 9.0,
                "sgst": 9.0,
                "igst": 0.0,
                "line_total": 118.0
            }
        ]
    }

    # B2B Sale - This should try to sync with Tally in the background
    response = client.post("/api/pos/sale", json=payload)
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["message"] == "Sale completed successfully"
    receipt = data["receipt"]
    
    assert receipt["invoice_type"] == "B2B"
    assert receipt["payment_reference"] == "UPI123456"
    assert receipt["company"]["gstin"] == "27AAAAA0000A1Z5" # Snapshot works
    assert receipt["tally"]["status"] in ["FAILED", "PENDING", "SUCCESS"]
    
    sale_id = receipt["id"]

    # History API Filter
    hist_res = client.get("/api/pos/history?invoice_type=B2B")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["items"]) >= 1

    # Single Invoice API
    inv_res = client.get(f"/api/pos/sales/{sale_id}")
    assert inv_res.status_code == 200
    assert inv_res.json()["receipt"]["id"] == sale_id

def test_b2c_pos_checkout_no_tally(client, setup_billing_data):
    payload = {
        "invoice_type": "B2C",
        "payment_method": "Cash",
        "total_taxable_amount": 200.0,
        "total_tax": 36.0,
        "grand_total": 236.0,
        "items": [
            {
                "product_id": setup_billing_data["product_id"],
                "sku": setup_billing_data["sku"],
                "product_name": "Test Product",
                "quantity": 2,
                "selling_price": 100.0,
                "discount": 0.0,
                "gst_rate": 18.0,
                "taxable_amount": 200.0,
                "cgst": 18.0,
                "sgst": 18.0,
                "igst": 0.0,
                "line_total": 236.0
            }
        ]
    }

    response = client.post("/api/pos/sale", json=payload)
    assert response.status_code == 200, response.json()
    data = response.json()
    receipt = data["receipt"]
    
    assert receipt["invoice_type"] == "B2C"
    # B2C should be NOT_APPLICABLE for Tally
    assert receipt["tally"]["status"] == "NOT_APPLICABLE"
