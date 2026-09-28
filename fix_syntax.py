test_path = "test_amazon_architecture.py"
with open(test_path, "r") as f:
    content = f.read()

content = content.replace("import app.services.amazon_service as svc; svc.get_amazon_client = lambda: TestMockClient()", "import app.services.amazon_service\n    app.services.amazon_service.get_amazon_client = lambda: TestMockClient()")

with open(test_path, "w") as f:
    f.write(content)
