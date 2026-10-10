import os
import re

file_path = "backend/app/main.py"
with open(file_path, "r") as f:
    content = f.read()

# Add import
if "from app.api.routers import fix_sku" not in content:
    content = content.replace("from app.api.routers import ", "from app.api.routers import fix_sku, ")

# Add route
if "app.include_router(fix_sku.router, prefix=\"/api\")" not in content:
    content = content.replace("app.include_router(auth.router, prefix=\"/api\")", "app.include_router(auth.router, prefix=\"/api\")\napp.include_router(fix_sku.router, prefix=\"/api\")")

with open(file_path, "w") as f:
    f.write(content)
