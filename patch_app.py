import re

file_path = "frontend/src/App.jsx"
with open(file_path, "r") as f:
    content = f.read()

import_str = "import AmazonLiveInventory from './pages/Amazon/AmazonLiveInventory';\n"
if "AmazonLiveInventory" not in content:
    content = content.replace(
        "import WarehouseMasterList from './pages/Warehouse/WarehouseMasterList';", 
        "import WarehouseMasterList from './pages/Warehouse/WarehouseMasterList';\n" + import_str
    )

route_str = '<Route path="/amazon/live-inventory" element={<AmazonLiveInventory />} />\n              '
if "/amazon/live-inventory" not in content:
    content = content.replace(
        '<Route path="/warehouses" element={<WarehouseMasterList />} />',
        '<Route path="/warehouses" element={<WarehouseMasterList />} />\n              ' + route_str
    )

with open(file_path, "w") as f:
    f.write(content)
