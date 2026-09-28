import re

file_path = "backend/app/main.py"
with open(file_path, "r") as f:
    content = f.read()

if "from app.api.routers import amazon\n" not in content:
    content = content.replace(
        "from app.api.routers import auth", 
        "from app.api.routers import amazon\nfrom app.api.routers import auth"
    )

if "app.include_router(amazon.router, prefix=\"/api\")" not in content:
    content = content.replace(
        "app.include_router(auth.router, prefix=\"/api\")", 
        "app.include_router(amazon.router, prefix=\"/api\")\napp.include_router(auth.router, prefix=\"/api\")"
    )

with open(file_path, "w") as f:
    f.write(content)
