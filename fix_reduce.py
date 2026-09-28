import re

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "r") as f:
    content = f.read()

content = content.replace(
    "const totals = cart.reduce((acc, item) => {",
    "const totals = (cart || []).reduce((acc, item) => {"
)

content = content.replace(
    "const hasUnconfirmedGst = cart.some(item => item.gst_needs_confirmation);",
    "const hasUnconfirmedGst = (cart || []).some(item => item.gst_needs_confirmation);"
)

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "w") as f:
    f.write(content)
