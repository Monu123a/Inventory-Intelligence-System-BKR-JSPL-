import re

file_path = "backend/app/services/amazon_service.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("sku = str(item.get(\"sku\", \"\")).strip().upper()[:6]", "sku = str(item.get(\"sku\", \"\")).strip().upper()")

# Remove the debug prints I added earlier
content = content.replace('print("SKIPPED AT:", locals()); skipped_count += 1', 'skipped_count += 1')
content = content.replace('logger.error(f"Failed to process item {sku} for order {order_id}: {e}"); print(f"EXCEPTION:", e)', 'logger.error(f"Failed to process item {sku} for order {order_id}: {e}")')

with open(file_path, "w") as f:
    f.write(content)
