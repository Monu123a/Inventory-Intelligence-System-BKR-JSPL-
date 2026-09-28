import re

file_path = "frontend/src/components/layout/Sidebar.jsx"
with open(file_path, "r") as f:
    content = f.read()

target = "{ path: ROUTES.AMAZON_RETURNS, label: 'Amazon Returns', icon: FiRefreshCw },"
replacement = "{ path: ROUTES.AMAZON_RETURNS, label: 'Amazon Returns', icon: FiRefreshCw },\n        { path: '/amazon/live-inventory', label: 'Live Inventory (SP-API)', icon: FiLayers },"

content = content.replace(target, replacement)

with open(file_path, "w") as f:
    f.write(content)
