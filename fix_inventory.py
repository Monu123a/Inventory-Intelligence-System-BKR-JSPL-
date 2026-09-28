import re
import os

# Fix stock reservation service
svc_path = "backend/app/services/stock_reservation_service.py"
with open(svc_path, "r") as f:
    content = f.read()

content = content.replace("Inventory.quantity", "Inventory.current_qty")

with open(svc_path, "w") as f:
    f.write(content)

# Fix test script
test_path = "test_amazon_architecture.py"
with open(test_path, "r") as f:
    content = f.read()

content = content.replace("inv.quantity", "inv.current_qty")
content = content.replace("quantity=100", "current_qty=100")

with open(test_path, "w") as f:
    f.write(content)
