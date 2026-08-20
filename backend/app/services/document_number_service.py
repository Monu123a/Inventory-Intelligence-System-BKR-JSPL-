from sqlalchemy.orm import Session
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError
from app.models.schema import DocumentSequence, DocumentTypeEnum, Company
import logging

logger = logging.getLogger(__name__)

class DocumentNumberService:
    @staticmethod
    def generate_number(
        db: Session,
        company_id: int,
        document_type: DocumentTypeEnum,
        fiscal_year: str,
        prefix_override: str = None
    ) -> str:
        company = db.query(Company).filter(Company.id == company_id).first()
        company_prefix = company.code if company and company.code else f"COMP{company_id}"
        
        if prefix_override:
            prefix = prefix_override
        else:
            if document_type != DocumentTypeEnum.SALE:
                prefix = f"{company_prefix}/{document_type.value}"
            else:
                prefix = company_prefix

        # Step 1: Atomic increment
        result = db.execute(
            update(DocumentSequence)
            .where(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year,
                DocumentSequence.prefix == prefix
            )
            .values(last_number=DocumentSequence.last_number + 1)
        )

        if result.rowcount > 0:
            seq = db.query(DocumentSequence).filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year,
                DocumentSequence.prefix == prefix
            ).first()
            if prefix.upper() in ['GST', 'JGST']:
                return f"{prefix}-{seq.last_number:03d}"
            return f"{prefix}/{fiscal_year}/{seq.last_number:05d}"

        # Step 2: No existing row — create one
        try:
            seq = DocumentSequence(
                company_id=company_id,
                document_type=document_type,
                fiscal_year=fiscal_year,
                prefix=prefix,
                last_number=1
            )
            db.add(seq)
            db.flush()
            if prefix.upper() in ['GST', 'JGST']:
                return f"{prefix}-001"
            return f"{prefix}/{fiscal_year}/00001"
        except IntegrityError:
            db.rollback()
            result = db.execute(
                update(DocumentSequence)
                .where(
                    DocumentSequence.company_id == company_id,
                    DocumentSequence.document_type == document_type,
                    DocumentSequence.fiscal_year == fiscal_year,
                    DocumentSequence.prefix == prefix
                )
                .values(last_number=DocumentSequence.last_number + 1)
            )

            seq = db.query(DocumentSequence).filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year,
                DocumentSequence.prefix == prefix
            ).first()

            if prefix.upper() in ['GST', 'JGST']:
                return f"{prefix}-{seq.last_number:03d}"
            return f"{prefix}/{fiscal_year}/{seq.last_number:05d}"

def _resolve_prefix(db, company_id, document_type, prefix_override, seq=None):
    """Determine the prefix for the document number."""
    if prefix_override:
        # Update stored prefix if it changed
        if seq and seq.prefix != prefix_override:
            seq.prefix = prefix_override
            db.add(seq)
            db.flush()
        return prefix_override

    if seq and seq.prefix:
        return seq.prefix

    company = db.query(Company).filter(Company.id == company_id).first()
    company_prefix = company.code if company and company.code else f"COMP{company_id}"

    if document_type != DocumentTypeEnum.SALE:
        return f"{company_prefix}/{document_type.value}"
    return company_prefix
