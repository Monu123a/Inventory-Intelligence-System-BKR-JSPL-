import re

file_path = "backend/app/main.py"
with open(file_path, "r") as f:
    content = f.read()

import_str = "from app.api.routers import amazon\n"
if "import amazon" not in content:
    content = content.replace("from app.api.routers import auth,", import_str + "from app.api.routers import auth,")

include_str = "app.include_router(amazon.router)\n"
if "app.include_router(amazon.router)" not in content:
    content = content.replace("app.include_router(auth.router)", include_str + "app.include_router(auth.router)")

with open(file_path, "w") as f:
    f.write(content)
