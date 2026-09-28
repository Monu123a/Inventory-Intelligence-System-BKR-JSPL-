import re

with open("frontend/src/App.jsx", "r") as f:
    content = f.read()

content = content.replace(
    "<Route path={ROUTES.POS_INVOICE} element={<InvoicePreviewPage />} />",
    "<Route path={ROUTES.POS_INVOICE} element={<InvoicePreviewPage />} />\n                <Route path=\"/sales/:id/edit\" element={<EditInvoicePage />} />"
)

with open("frontend/src/App.jsx", "w") as f:
    f.write(content)

print("Fixed route in App.jsx")
