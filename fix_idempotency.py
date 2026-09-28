import re

file_path = "backend/app/services/amazon_reconciliation_service.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    'reference_id=f"{order_id}_{sku}_{line_item_id}_DEDUCT"', 
    'reference_id=f"{order_id}_{sku}_{line_item_id}_DEDUCT_{new_reconciled}"'
)

with open(file_path, "w") as f:
    f.write(content)
