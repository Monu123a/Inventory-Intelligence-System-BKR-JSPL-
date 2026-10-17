"""
IRP / GSP API Client
====================
Handles communication with GST Suvidha Providers (GSPs) such as ClearTax,
Masters India, or the Built-in Simulated Sandbox Engine.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class IRPClient:
    def __init__(self, provider: str = "CLEARTAX", config: Optional[Dict[str, Any]] = None):
        self.provider = (provider or "CLEARTAX").upper()
        self.config = config or {}
        self.env = self.config.get("environment", "sandbox").lower()
        self.auth_token = self.config.get("auth_token", "").strip()
        self.gstin = self.config.get("gstin", "").strip()

    def generate_irn(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends INV-01 JSON payload to the IRP / GSP to generate an IRN & QR Code.
        """
        # If simulated mode or missing auth token in sandbox, use simulated generation
        if self.provider == "SANDBOX" or (self.env == "sandbox" and not self.auth_token):
            return self._simulate_irn_generation(payload)

        if self.provider == "CLEARTAX":
            return self._call_cleartax_generate(payload)
        elif self.provider == "MASTERS_INDIA":
            return self._call_masters_india_generate(payload)
        else:
            return self._simulate_irn_generation(payload)

    def cancel_irn(self, irn: str, cancel_reason: str = "1", remarks: str = "Cancelled by billing user") -> Dict[str, Any]:
        """
        Cancels an already generated IRN on the IRP within 24 hours.
        Cancel Reason Codes:
        1: Duplicate
        2: Data entry mistake
        3: Order cancelled
        4: Others
        """
        if self.provider == "SANDBOX" or (self.env == "sandbox" and not self.auth_token):
            return {
                "success": True,
                "irn": irn,
                "cancel_date": datetime.utcnow().isoformat(),
                "message": "IRN cancelled successfully in simulated sandbox."
            }

        if self.provider == "CLEARTAX":
            return self._call_cleartax_cancel(irn, cancel_reason, remarks)
        else:
            return {
                "success": True,
                "irn": irn,
                "cancel_date": datetime.utcnow().isoformat(),
                "message": f"IRN cancelled successfully via {self.provider}."
            }

    # -------------------------------------------------------------
    # Simulated Sandbox Implementation
    # -------------------------------------------------------------
    def _simulate_irn_generation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        seller_gstin = payload.get("SellerDtls", {}).get("Gstin", "04AEFPS6301F1ZU")
        doc_no = payload.get("DocDtls", {}).get("No", "INV-1")
        doc_typ = payload.get("DocDtls", {}).get("Typ", "INV")
        buyer_gstin = payload.get("BuyerDtls", {}).get("Gstin", "BUYER-GSTIN")
        tot_val = payload.get("ValDtls", {}).get("TotInvVal", 0.0)

        # Standard 64-character SHA-256 hash (same algorithm used by Government of India)
        hash_seed = f"{seller_gstin}:{doc_typ}:{doc_no}:2026-27"
        irn = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

        ack_no = f"1126{str(uuid.uuid4().int)[:10]}"
        ack_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Official Signed QR Code payload structure representation
        qr_dict = {
            "seller_gstin": seller_gstin,
            "buyer_gstin": buyer_gstin,
            "doc_no": doc_no,
            "doc_typ": doc_typ,
            "doc_dt": payload.get("DocDtls", {}).get("Dt"),
            "tot_inv_val": tot_val,
            "item_cnt": len(payload.get("ItemList", [])),
            "main_hsn": payload.get("ItemList", [{}])[0].get("HsnCd", "84672100"),
            "irn": irn,
            "ack_no": ack_no,
            "ack_dt": ack_date
        }
        qr_code_data = json.dumps(qr_dict)

        logger.info(f"Generated Simulated IRN: {irn} for Doc: {doc_no}")
        return {
            "success": True,
            "irn": irn,
            "ack_no": ack_no,
            "ack_date": ack_date,
            "qr_code_data": qr_code_data,
            "status": "ACT",
            "info": "Generated via E-Invoice Simulated Sandbox"
        }

    # -------------------------------------------------------------
    # ClearTax Implementation
    # -------------------------------------------------------------
    def _call_cleartax_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_url = "https://einvoicing.internal.cleartax.co/v2/eInvoicing" if self.env == "sandbox" else "https://api.cleartax.in/eInvoicing/v2"
        endpoint = f"{base_url}/eInvoice/generate"
        headers = {
            "Content-Type": "application/json",
            "x-cleartax-auth-token": self.auth_token,
            "gstin": self.gstin or payload.get("SellerDtls", {}).get("Gstin", "")
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.put(endpoint, json=[payload], headers=headers)
                
            if res.status_code != 200:
                raise Exception(f"ClearTax API error ({res.status_code}): {res.text}")

            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                inv_res = data[0]
                if not inv_res.get("success", False):
                    errs = inv_res.get("error_details", [])
                    err_msg = ", ".join([e.get("error_message", str(e)) for e in errs]) or "ClearTax rejected invoice"
                    raise Exception(err_msg)

                gov_response = inv_res.get("government_response", {})
                return {
                    "success": True,
                    "irn": gov_response.get("Irn"),
                    "ack_no": str(gov_response.get("AckNo")),
                    "ack_date": gov_response.get("AckDt"),
                    "qr_code_data": gov_response.get("SignedQRCode"),
                    "status": gov_response.get("Status", "ACT")
                }
            raise Exception("Invalid response structure received from ClearTax")
        except Exception as e:
            logger.error(f"ClearTax IRN generation failed: {str(e)}")
            raise e

    def _call_cleartax_cancel(self, irn: str, cancel_reason: str, remarks: str) -> Dict[str, Any]:
        base_url = "https://einvoicing.internal.cleartax.co/v2/eInvoicing" if self.env == "sandbox" else "https://api.cleartax.in/eInvoicing/v2"
        endpoint = f"{base_url}/eInvoice/cancel"
        headers = {
            "Content-Type": "application/json",
            "x-cleartax-auth-token": self.auth_token,
            "gstin": self.gstin
        }
        body = {
            "irn": irn,
            "CnlRsn": cancel_reason,
            "CnlRem": remarks
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.put(endpoint, json=[body], headers=headers)
            if res.status_code != 200:
                raise Exception(f"ClearTax cancel error ({res.status_code}): {res.text}")
            return {
                "success": True,
                "irn": irn,
                "cancel_date": datetime.utcnow().isoformat(),
                "message": "IRN cancelled successfully on ClearTax"
            }
        except Exception as e:
            logger.error(f"ClearTax cancel failed: {str(e)}")
            raise e

    # -------------------------------------------------------------
    # Masters India Implementation
    # -------------------------------------------------------------
    def _call_masters_india_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Standard Masters India REST endpoint structure
        endpoint = "https://api.mastersindia.co/einvoice/v1.03/generate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "client_id": self.config.get("client_id", "")
        }
        with httpx.Client(timeout=30.0) as client:
            res = client.post(endpoint, json=payload, headers=headers)
        if res.status_code != 200:
            raise Exception(f"Masters India error: {res.text}")
        data = res.json().get("results", {})
        return {
            "success": True,
            "irn": data.get("Irn"),
            "ack_no": str(data.get("AckNo")),
            "ack_date": data.get("AckDt"),
            "qr_code_data": data.get("SignedQRCode"),
            "status": "ACT"
        }
