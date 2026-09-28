import re

file_path = "backend/app/services/amazon_service.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("skipped_count += 1", 'print("SKIPPED AT:", locals()); skipped_count += 1')
content = content.replace('logger.error(f"Failed to process item {sku} for order {order_id}: {e}")', 'logger.error(f"Failed to process item {sku} for order {order_id}: {e}"); print(f"EXCEPTION:", e)')

with open(file_path, "w") as f:
    f.write(content)
