test_path = "test_amazon_architecture.py"
with open(test_path, "r") as f:
    content = f.read()

content = content.replace("inv = Inventory(company_id=company_id, product_id=product.id, warehouse_id=warehouse.id, current_qty=100)", "inv = Inventory(company_id=company_id, product_id=product.id, warehouse_id=warehouse.id); inv._allow_mutation = True; inv.current_qty = 100")
content = content.replace("inv.current_qty = 100", "inv._allow_mutation = True; inv.current_qty = 100")

with open(test_path, "w") as f:
    f.write(content)
