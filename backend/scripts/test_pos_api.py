from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_pos_validation():
    # Attempt to hit the POS sale endpoint without a cart
    payload = {
        "invoice_type": "B2C",
        "total_taxable_amount": 0,
        "total_tax": 0,
        "grand_total": 0,
        "payment_method": "Cash",
        "items": []
    }
    headers = {"X-Company-Id": "3"}
    
    response = client.post("/api/pos/sale", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_pos_validation()
