import uuid
import random
from datetime import datetime, timedelta

def get_mock_shipped_orders(last_sync_time=None):
    """
    Simulates a response from the Amazon SP-API Orders endpoint.
    Returns a list of shipped order items, theoretically filtered by last_sync_time.
    """
    # Some sample SKUs that might exist in the system
    sample_skus = ["  PROD-001 ", "prod-002", "TEST-SKU-123  "]
    
    orders = []
    num_orders = random.randint(1, 5)
    
    for _ in range(num_orders):
        order_id = f"AMZ-{random.randint(100, 999)}-{random.randint(1000000, 9999999)}"
        sku = random.choice(sample_skus)
        quantity = random.randint(1, 3)
        
        orders.append({
            "AmazonOrderId": order_id,
            "OrderStatus": "Shipped",
            "PurchaseDate": (datetime.utcnow() - timedelta(minutes=random.randint(5, 25))).isoformat(),
            "NextToken": f"token-{random.randint(1000, 9999)}" if random.random() > 0.5 else None,
            "OrderItems": [
                {
                    "OrderItemId": f"{random.randint(10000000000000, 99999999999999)}",
                    "SellerSKU": sku,
                    "QuantityOrdered": quantity,
                    "QuantityShipped": quantity
                }
            ]
        })
        
    return orders
