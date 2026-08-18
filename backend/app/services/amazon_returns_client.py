import abc
import os
from typing import List, Dict, Any
from datetime import datetime

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

class MockAmazonReturnsClient(AmazonReturnsClient):
    def fetch_returns(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Mock client. Disabled per user request to prevent dummy data generation.
        """
        return []

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
