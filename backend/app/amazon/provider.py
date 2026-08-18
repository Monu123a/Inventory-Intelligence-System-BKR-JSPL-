import time
import os
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.amazon.auth import AmazonAuthenticator
import yaml

logger = logging.getLogger("amazon.provider")

class AmazonProvider(ABC):
    @abstractmethod
    def download_data(self) -> Optional[Dict[str, Any]]:
        """
        Executes the API lifecycle to retrieve the requested data.
        Returns a dictionary with document details (e.g. url, compression_algorithm) or None on failure.
        """

class ReportsAPIProvider(AmazonProvider):
    def __init__(self, authenticator: AmazonAuthenticator):
        self.auth = authenticator
        
        # Load config
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "amazon_config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        self.endpoint = os.getenv("SP_API_ENDPOINT", "https://sellingpartnerapi-eu.amazon.com")
        self.marketplace_id = config["amazon"]["marketplace_id"]
        self.report_type = config["amazon"]["report_type"]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-amz-access-token": self.auth.get_access_token(),
            "Content-Type": "application/json"
        }

    def _create_report(self) -> str:
        url = f"{self.endpoint}/reports/2021-06-30/reports"
        payload = {
            "reportType": self.report_type,
            "marketplaceIds": [self.marketplace_id]
        }
        logger.info(f"Creating report request for {self.report_type}...")
        
        response = requests.post(url, json=payload, headers=self._get_headers(), auth=self.auth.get_sigv4_auth())
        response.raise_for_status()
        
        report_id = response.json()["reportId"]
        logger.info(f"Report request created. Report ID: {report_id}")
        return report_id

    def _poll_report_status(self, report_id: str) -> str:
        url = f"{self.endpoint}/reports/2021-06-30/reports/{report_id}"
        
        while True:
            logger.info(f"Checking status for Report ID: {report_id}")
            response = requests.get(url, headers=self._get_headers(), auth=self.auth.get_sigv4_auth())
            response.raise_for_status()
            
            status = response.json()["processingStatus"]
            logger.info(f"Status: {status}")
            
            if status in ["DONE", "CANCELLED", "FATAL"]:
                if status != "DONE":
                    logger.error(f"Report generation failed with status: {status}")
                    raise Exception(f"Report failed: {status}")
                return response.json()["reportDocumentId"]
                
            time.sleep(30) # Poll every 30 seconds

    def _get_document_details(self, document_id: str) -> Dict[str, Any]:
        url = f"{self.endpoint}/reports/2021-06-30/documents/{document_id}"
        logger.info(f"Retrieving document details for Document ID: {document_id}")
        
        response = requests.get(url, headers=self._get_headers(), auth=self.auth.get_sigv4_auth())
        response.raise_for_status()
        
        return response.json()

    def download_data(self) -> Optional[Dict[str, Any]]:
        try:
            report_id = self._create_report()
            document_id = self._poll_report_status(report_id)
            doc_details = self._get_document_details(document_id)
            return doc_details
        except Exception as e:
            logger.error(f"Error during Reports API lifecycle: {e}")
            return None
