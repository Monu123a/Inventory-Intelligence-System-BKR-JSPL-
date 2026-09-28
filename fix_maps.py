import re

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "r") as f:
    content = f.read()

# Fix activeWarehouses map
content = content.replace(
    "{activeWarehouses.map(w => (",
    "{(activeWarehouses || []).map(w => ("
)

# Fix searchResults map
content = content.replace(
    "{searchResults.map(result => (",
    "{(searchResults || []).map(result => ("
)

# Fix cart map
content = content.replace(
    "{cart.map((item, index) => (",
    "{(cart || []).map((item, index) => ("
)

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "w") as f:
    f.write(content)
