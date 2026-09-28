import abc
import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AmazonClient(abc.ABC):
    @abc.abstractmethod
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetch recent orders from Amazon.
        Each order should be a dict containing at least:
        - order_id: str
        - items: List[Dict] with 'sku' and 'quantity'
        """

class MockAmazonClient(AmazonClient):
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Mock client disabled to prevent polluting the production database with fake orders.
        """
        return []

class SPAPIAmazonClient(AmazonClient):
    def __init__(self):
        try:
            from sp_api.api import Orders
            self.Orders = Orders
        except ImportError:
            logger.error("sp-api-python package is not installed. Run: pip install python-amazon-sp-api")
            self.Orders = None
            
        self.credentials = dict(
            refresh_token=os.getenv("LWA_REFRESH_TOKEN"),
            lwa_app_id=os.getenv("LWA_CLIENT_ID"),
            lwa_client_secret=os.getenv("LWA_CLIENT_SECRET"),
            aws_secret_key=os.getenv("AWS_SECRET_KEY"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY"),
            role_arn=os.getenv("AWS_IAM_ROLE_ARN"),
        )
        self.marketplace = os.getenv("MARKETPLACE_ID", "IN")
        
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetches real orders from Amazon SP-API OrdersV0.
        """
        if not self.Orders:
            logger.error("Cannot fetch orders. SP-API library missing.")
            return []
            
        try:
            from sp_api.base import Marketplaces
            marketplace = getattr(Marketplaces, self.marketplace, Marketplaces.IN)
            orders_api = self.Orders(credentials=self.credentials, marketplace=marketplace)
            
            created_after = since.isoformat() if since else (datetime.utcnow() - timedelta(days=7)).isoformat()
            
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
            
            return parsed_orders
        except Exception as e:
            logger.error(f"Failed to fetch orders from SP-API: {e}")
            return []

def get_amazon_client() -> AmazonClient:
    client_type = os.getenv("AMAZON_CLIENT", "mock").lower()
    if client_type == "spapi":
        return SPAPIAmazonClient()
    return MockAmazonClient()
