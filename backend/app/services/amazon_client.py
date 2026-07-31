import abc
import os
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta

class AmazonClient(abc.ABC):
    @abc.abstractmethod
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetch recent orders from Amazon.
        Each order should be a dict containing at least:
        - order_id: str
        - items: List[Dict] with 'sku' and 'quantity'
        """
        pass

class MockAmazonClient(AmazonClient):
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Mock client disabled to prevent polluting the production database with fake orders.
        """
        return []

class SPAPIAmazonClient(AmazonClient):
    def __init__(self):
        # Here we would initialize the sp-api-python client using env variables
        self.credentials = {
            "refresh_token": os.getenv("SP_API_REFRESH_TOKEN"),
            "lwa_app_id": os.getenv("SP_API_LWA_APP_ID"),
            "lwa_client_secret": os.getenv("SP_API_LWA_CLIENT_SECRET"),
            "aws_access_key": os.getenv("SP_API_AWS_ACCESS_KEY"),
            "aws_secret_key": os.getenv("SP_API_AWS_SECRET_KEY"),
            "role_arn": os.getenv("SP_API_ROLE_ARN")
        }
        
    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetches real orders from Amazon SP-API OrdersV0.
        """
        # Placeholder for real SP-API integration.
        # e.g., res = Orders(credentials=self.credentials).get_orders(CreatedAfter=since)
        # return parse_res(res)
        return []

def get_amazon_client() -> AmazonClient:
    client_type = os.getenv("AMAZON_CLIENT", "mock").lower()
    if client_type == "spapi":
        return SPAPIAmazonClient()
    return MockAmazonClient()
