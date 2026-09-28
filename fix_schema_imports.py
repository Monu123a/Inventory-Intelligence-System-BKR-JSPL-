import re

file_path = "backend/app/models/schema.py"
with open(file_path, "r") as f:
    content = f.read()

if "Index" not in content[:500]:
    content = content.replace("from sqlalchemy import Column", "from sqlalchemy import Column, Index")

with open(file_path, "w") as f:
    f.write(content)
