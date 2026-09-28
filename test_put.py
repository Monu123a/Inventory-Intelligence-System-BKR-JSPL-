import requests
import json

url = "http://localhost:8000/api/pos/sales/50"
headers = {"X-Company-Id": "2", "Content-Type": "application/json"}
payload = {
  "invoice_type": "B2C",
  "total_taxable_amount": 0,
  "total_tax": 0,
  "grand_total": 0,
  "items": [
    {
      "product_id": 1,
      "sku": "TEST",
      "quantity": 1,
      "selling_price": 100,
      "gst_rate": 0,
      "taxable_amount": 100,
      "cgst": 0,
      "sgst": 0,
      "line_total": 100
    }
  ]
}

try:
    res = requests.put(url, headers=headers, json=payload)
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
