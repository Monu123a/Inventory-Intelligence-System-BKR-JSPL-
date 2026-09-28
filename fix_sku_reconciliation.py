import re

file_path = "backend/app/services/amazon_reconciliation_service.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace('sku = str(report_item.get("sku", "")).strip().upper()[:6]', 'sku = str(report_item.get("sku", "")).strip().upper()')

with open(file_path, "w") as f:
    f.write(content)
