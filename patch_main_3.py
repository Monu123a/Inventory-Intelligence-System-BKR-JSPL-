import re

file_path = "backend/app/main.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from app.api.routers.companies import router as companies_router",
    "from app.api.routers.companies import router as companies_router\nfrom app.api.routers import amazon"
)

content = content.replace(
    "app.include_router(companies_router, prefix=\"/api/companies\")",
    "app.include_router(companies_router, prefix=\"/api/companies\")\napp.include_router(amazon.router, prefix=\"/api\")"
)

with open(file_path, "w") as f:
    f.write(content)
