import re

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "r") as f:
    content = f.read()

content = content.replace("api.get(`/api/sales/${id}/invoice`)", "api.get(`/api/pos/sales/${id}`)")
content = content.replace("const sale = res.data;", "const sale = res.data.receipt || res.data;")

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "w") as f:
    f.write(content)
