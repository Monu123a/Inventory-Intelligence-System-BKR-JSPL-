import re

with open("frontend/src/pages/POS/EditInvoicePage.jsx", "r") as f:
    content = f.read()

# Add const { id } = useParams();
# Find const navigate = useNavigate();
content = content.replace("const navigate = useNavigate();", "const navigate = useNavigate();\n  const { id } = useParams();\n  const [isLoaded, setIsLoaded] = React.useState(false);")

with open("frontend/src/pages/POS/EditInvoicePage.jsx", "w") as f:
    f.write(content)

print("Hooks fixed")
