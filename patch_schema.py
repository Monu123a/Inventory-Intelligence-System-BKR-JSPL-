import re

file_path = "backend/app/api/routers/warehouses.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("    external_code: str", "    external_code: str\n    amazon_network: Optional[str] = None")

with open(file_path, "w") as f:
    f.write(content)
