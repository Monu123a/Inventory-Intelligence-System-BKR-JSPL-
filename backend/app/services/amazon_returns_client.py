import abc
import os
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta

class AmazonReturnsClient(abc.ABC):
    @abc.abstractmethod
    def fetch_returns(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetch recent returns from Amazon.
        Each return should be a dict containing at least:
        - amazon_return_id: str
        - amazon_order_id: str
        - order_item_id: str
        - sku: str
        - asin: str
        - product_name: str
        - quantity: int
        - return_reason: str
        - return_status: str ("In Transit", "Received")
        - requested_at: datetime string
        - received_at: datetime string (optional)
        """
        pass

class MockAmazonReturnsClient(AmazonReturnsClient):
    def fetch_returns(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Mock client for returning dummy amazon returns data.
        """
        # Generate some dummy data
        now = datetime.utcnow()
        dummy_returns = []
        
        # We'll create a few random returns
        statuses = ["In Transit", "Received"]
        reasons = ["DEFECTIVE", "NO_LONGER_NEEDED", "SWITCHEROO", "MISSED_ESTIMATED_DELIVERY", "DAMAGED_BY_CARRIER"]
        
        for i in range(1, random.randint(3, 8)):
            status = random.choice(statuses)
            requested = now - timedelta(days=random.randint(1, 10))
            received = requested + timedelta(days=random.randint(1, 4)) if status == "Received" else None
            
            dummy_returns.append({
                "amazon_return_id": f"RMA-{random.randint(1000000, 9999999)}",
                "amazon_order_id": f"404-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                "order_item_id": f"{random.randint(10000000000000, 99999999999999)}",
                "sku": f"SKU-MOCK-{random.randint(100, 999)}",
                "asin": f"B0{random.randint(10000000, 99999999)}",
                "product_name": f"Mock Product {i}",
                "quantity": random.randint(1, 3),
                "return_reason": random.choice(reasons),
                "return_status": status,
                "requested_at": requested.isoformat(),
                "received_at": received.isoformat() if received else None
            })
            
        return dummy_returns

class SPAPIAmazonReturnsClient(AmazonReturnsClient):
    def __init__(self):
        self.credentials = {
            "refresh_token": os.getenv("SP_API_REFRESH_TOKEN"),
            "lwa_app_id": os.getenv("SP_API_LWA_APP_ID"),
            "lwa_client_secret": os.getenv("SP_API_LWA_CLIENT_SECRET"),
            "aws_access_key": os.getenv("SP_API_AWS_ACCESS_KEY"),
            "aws_secret_key": os.getenv("SP_API_AWS_SECRET_KEY"),
            "role_arn": os.getenv("SP_API_ROLE_ARN")
        }
        
    def fetch_returns(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetches real returns from Amazon SP-API.
        """
        # Placeholder for real SP-API integration.
        return []

def get_amazon_returns_client() -> AmazonReturnsClient:
    client_type = os.getenv("AMAZON_CLIENT", "mock").lower()
    if client_type == "spapi":
        return SPAPIAmazonReturnsClient()
    return MockAmazonReturnsClient()
