import re

files = [
    "frontend/src/pages/Warehouse/WarehouseMasterList.jsx",
    "frontend/src/pages/Amazon/AmazonLiveInventory.jsx"
]

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()
    
    content = content.replace("import { api }", "import api")
    
    with open(file_path, "w") as f:
        f.write(content)
