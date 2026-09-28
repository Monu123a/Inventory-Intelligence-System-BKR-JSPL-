import re

with open("backend/app/api/routers/pos.py", "r") as f:
    content = f.read()

content = content.replace("event_type = \"SALE\" if delta_qty > 0 else \"SALE_EDIT_RESTORE\"", "event_type = \"SALE\" if delta_qty > 0 else \"ADD\"")

with open("backend/app/api/routers/pos.py", "w") as f:
    f.write(content)

print("Fixed event type assignment")
