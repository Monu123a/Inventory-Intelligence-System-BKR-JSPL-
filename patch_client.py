import re

file_path = "backend/app/services/amazon_client.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace get_orders call to include all statuses and add exponential backoff
old_fetch_logic = """
            res = orders_api.get_orders(CreatedAfter=created_after, OrderStatuses=["Shipped", "Unshipped", "PartiallyShipped"])
            orders_data = res.payload.get("Orders", [])
            
            parsed_orders = []
            for amazon_order in orders_data:
                order_id = amazon_order.get("AmazonOrderId")
                status = amazon_order.get("OrderStatus")
                
                # Fetch order items
                import time; time.sleep(1.5); items_res = orders_api.get_order_items(order_id)
                items_data = items_res.payload.get("OrderItems", [])
                
                parsed_items = []
                for item in items_data:
                    parsed_items.append({
                        "sku": item.get("SellerSKU"),
                        "quantity": item.get("QuantityOrdered", 1),
                        "price": float(item.get("ItemPrice", {}).get("Amount", 0.0) if item.get("ItemPrice") else 0.0),
                        "title": item.get("Title")
                    })
                
                parsed_orders.append({
                    "order_id": order_id,
                    "status": status,
                    "items": parsed_items,
                    "purchase_date": amazon_order.get("PurchaseDate"),
                    "total": float(amazon_order.get("OrderTotal", {}).get("Amount", 0.0) if amazon_order.get("OrderTotal") else 0.0)
                })
"""

new_fetch_logic = """
            # Rate limiting / Backoff wrapper
            import time
            def fetch_with_backoff(call_fn, *args, **kwargs):
                retries = 3
                for attempt in range(retries):
                    try:
                        return call_fn(*args, **kwargs)
                    except Exception as e:
                        if "TooManyRequests" in str(e) or "QuotaExceeded" in str(e):
                            if attempt < retries - 1:
                                time.sleep(2 ** attempt)
                                continue
                        raise e

            res = fetch_with_backoff(orders_api.get_orders, CreatedAfter=created_after, OrderStatuses=["Pending", "Unshipped", "PartiallyShipped", "Shipped", "Canceled"])
            orders_data = res.payload.get("Orders", [])
            
            parsed_orders = []
            for amazon_order in orders_data:
                order_id = amazon_order.get("AmazonOrderId")
                status = amazon_order.get("OrderStatus")
                fulfillment_channel = amazon_order.get("FulfillmentChannel", "MFN") # MFN or AFN
                
                # Fetch order items
                time.sleep(1.5) # Basic rate limit
                items_res = fetch_with_backoff(orders_api.get_order_items, order_id)
                items_data = items_res.payload.get("OrderItems", [])
                
                parsed_items = []
                for item in items_data:
                    parsed_items.append({
                        "amazon_line_item_id": item.get("OrderItemId", "default"),
                        "sku": item.get("SellerSKU"),
                        "quantity": item.get("QuantityOrdered", 1),
                        "price": float(item.get("ItemPrice", {}).get("Amount", 0.0) if item.get("ItemPrice") else 0.0),
                        "title": item.get("Title")
                    })
                
                parsed_orders.append({
                    "order_id": order_id,
                    "status": status,
                    "fulfillment_channel": fulfillment_channel,
                    "items": parsed_items,
                    "purchase_date": amazon_order.get("PurchaseDate"),
                    "total": float(amazon_order.get("OrderTotal", {}).get("Amount", 0.0) if amazon_order.get("OrderTotal") else 0.0),
                    "last_update_date": amazon_order.get("LastUpdateDate")
                })
"""

content = content.replace(old_fetch_logic, new_fetch_logic)

with open(file_path, "w") as f:
    f.write(content)

