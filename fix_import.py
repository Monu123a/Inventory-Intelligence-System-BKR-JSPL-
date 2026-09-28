import re

with open("frontend/src/pages/POS/InvoicePreviewPage.jsx", "r") as f:
    content = f.read()

content = content.replace("FiEye\n} from", "FiEye,\n  FiXCircle\n} from")

with open("frontend/src/pages/POS/InvoicePreviewPage.jsx", "w") as f:
    f.write(content)
print("Fixed import")
