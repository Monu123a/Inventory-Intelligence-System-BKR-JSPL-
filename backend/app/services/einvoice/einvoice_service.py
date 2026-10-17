"""
E-Invoice Orchestration Service
===============================
Manages e-invoice generation, cancellation, status verification, and
database persistence for B2B sales in the Inventory Intelligence System.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.schema import Sale, CompanySettings
from app.services.einvoice.payload_builder import build_einvoice_payload
from app.services.einvoice.irp_client import IRPClient

logger = logging.getLogger(__name__)

class EInvoiceService:
    @staticmethod
    def generate_irn_for_sale(sale_id: int, db: Session, force_retry: bool = False) -> Dict[str, Any]:
        """
        Generates and saves the Government IRN and QR Code for a given Sale.
        """
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError(f"Sale with ID {sale_id} not found.")

        # Check if already generated
        if sale.einvoice_irn and sale.einvoice_status == "GENERATED" and not force_retry:
            return {
                "status": "ALREADY_GENERATED",
                "irn": sale.einvoice_irn,
                "ack_no": sale.einvoice_ack_no,
                "ack_date": sale.einvoice_ack_date.isoformat() if sale.einvoice_ack_date else None,
                "qr_code_data": sale.einvoice_qr_code_data,
                "message": "E-Invoice already active for this document."
            }

        # Validate B2B Eligibility
        buyer_gstin = (sale.customer_gstin or "").strip()
        if not buyer_gstin or len(buyer_gstin) < 15:
            raise ValueError(
                f"E-Invoicing is only applicable for B2B sales with a valid 15-character GSTIN. "
                f"Current buyer GSTIN: '{buyer_gstin or 'None'}'"
            )

        # Retrieve Company Settings & E-Invoice Config
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == sale.company_id).first()
        config = settings.einvoice_config if (settings and settings.einvoice_config) else {}
        provider = (settings.einvoice_provider if settings else "CLEARTAX") or "CLEARTAX"

        # Construct INV-01 Payload
        payload = build_einvoice_payload(sale, db=db)

        # Call IRP / GSP Client
        client = IRPClient(provider=provider, config=config)
        try:
            result = client.generate_irn(payload)
            
            # Parse Ack Date safely
            ack_date = datetime.utcnow()
            raw_ack_date = result.get("ack_date")
            if raw_ack_date:
                try:
                    ack_date = datetime.fromisoformat(str(raw_ack_date).replace(" ", "T"))
                except Exception:
                    try:
                        ack_date = datetime.strptime(str(raw_ack_date), "%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass

            # Update Sale record
            sale.einvoice_irn = result["irn"]
            sale.einvoice_ack_no = str(result["ack_no"])
            sale.einvoice_ack_date = ack_date
            sale.einvoice_qr_code_data = result["qr_code_data"]
            sale.einvoice_status = "GENERATED"
            sale.einvoice_error_message = None

            db.commit()
            db.refresh(sale)

            logger.info(f"Successfully generated and persisted IRN {sale.einvoice_irn} for Sale {sale.id}")
            return {
                "status": "SUCCESS",
                "irn": sale.einvoice_irn,
                "ack_no": sale.einvoice_ack_no,
                "ack_date": sale.einvoice_ack_date.isoformat() if sale.einvoice_ack_date else None,
                "qr_code_data": sale.einvoice_qr_code_data,
                "message": "E-Invoice (IRN & Signed QR Code) generated successfully!"
            }

        except Exception as e:
            sale.einvoice_status = "FAILED"
            sale.einvoice_error_message = str(e)
            db.commit()
            logger.error(f"Failed to generate IRN for Sale {sale.id}: {str(e)}")
            raise e

    @staticmethod
    def cancel_irn_for_sale(sale_id: int, cancel_reason: str, remarks: str, db: Session) -> Dict[str, Any]:
        """
        Cancels the active Government IRN for a sale.
        """
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError(f"Sale with ID {sale_id} not found.")

        if not sale.einvoice_irn:
            raise ValueError("Cannot cancel E-Invoice: No active IRN found for this sale.")

        if sale.einvoice_status == "CANCELLED":
            return {"status": "ALREADY_CANCELLED", "message": "IRN is already marked as cancelled."}

        settings = db.query(CompanySettings).filter(CompanySettings.company_id == sale.company_id).first()
        config = settings.einvoice_config if (settings and settings.einvoice_config) else {}
        provider = (settings.einvoice_provider if settings else "CLEARTAX") or "CLEARTAX"

        client = IRPClient(provider=provider, config=config)
        try:
            res = client.cancel_irn(irn=sale.einvoice_irn, cancel_reason=cancel_reason, remarks=remarks)
            sale.einvoice_status = "CANCELLED"
            sale.einvoice_canceled_at = datetime.utcnow()
            sale.einvoice_cancel_reason = f"[{cancel_reason}] {remarks}"
            db.commit()
            db.refresh(sale)
            return {
                "status": "SUCCESS",
                "irn": sale.einvoice_irn,
                "message": res.get("message", "E-Invoice IRN cancelled successfully.")
            }
        except Exception as e:
            logger.error(f"Failed to cancel IRN for Sale {sale.id}: {str(e)}")
            raise e
