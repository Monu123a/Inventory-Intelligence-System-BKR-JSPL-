import re

file_path = "frontend/src/pages/Warehouse/StateHubsPage.jsx"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("const { api } = await import('../../services/api');", "const { default: api } = await import('../../services/api');")
content = content.replace("await api.default.put", "await api.put")

with open(file_path, "w") as f:
    f.write(content)
