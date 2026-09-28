import re

file_path = "frontend/src/App.jsx"
with open(file_path, "r") as f:
    content = f.read()

import_str = "const AmazonLiveInventory = lazy(() => import('./pages/Amazon/AmazonLiveInventory'));\n"
if "AmazonLiveInventory" not in content:
    content = content.replace(
        "const WarehouseMasterList = lazy(() => import('./pages/Warehouse/WarehouseMasterList'));", 
        import_str + "const WarehouseMasterList = lazy(() => import('./pages/Warehouse/WarehouseMasterList'));"
    )

route_str = '<Route path="/amazon/live-inventory" element={<AmazonLiveInventory />} />\n                '
if "/amazon/live-inventory" not in content:
    content = content.replace(
        '<Route path={ROUTES.WAREHOUSE_MASTER_LIST} element={<WarehouseMasterList />} />',
        route_str + '<Route path={ROUTES.WAREHOUSE_MASTER_LIST} element={<WarehouseMasterList />} />'
    )

with open(file_path, "w") as f:
    f.write(content)
