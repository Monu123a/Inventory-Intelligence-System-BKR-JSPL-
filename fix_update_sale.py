import re

with open("backend/app/api/routers/pos.py", "r") as f:
    content = f.read()

content = content.replace("event_type=\"SALE_EDIT_RESTORE\"", "event_type=\"ADD\"")
content = content.replace("is_outbound=(delta_qty > 0)", "")
content = content.replace("is_outbound=False", "")

with open("backend/app/api/routers/pos.py", "w") as f:
    f.write(content)

print("Fixed event type in update_sale")
