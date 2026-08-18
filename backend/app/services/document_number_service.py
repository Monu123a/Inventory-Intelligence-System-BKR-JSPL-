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
        """
        Generates a strictly sequential document number using atomic UPDATE.
        Format: {PREFIX}/{FISCAL_YEAR}/{NUMBER}
        Example: BKR/26-27/00001

        Strategy:
        1. Attempt atomic UPDATE ... SET last_number = last_number + 1
        2. If no row matched (rowcount == 0), INSERT a new sequence with last_number = 1
        3. If INSERT conflicts (concurrent create), retry the UPDATE
        """
        # Step 1: Atomic increment (single SQL statement — no read-modify-write race)
        result = db.execute(
            update(DocumentSequence)
            .where(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year
            )
            .values(last_number=DocumentSequence.last_number + 1)
        )

        if result.rowcount > 0:
            # Row existed and was incremented atomically. Fetch the new number.
            seq = db.query(DocumentSequence).filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year
            ).first()

            prefix = _resolve_prefix(db, company_id, document_type, prefix_override, seq)
            return f"{prefix}/{fiscal_year}/{seq.last_number:05d}"

        # Step 2: No existing row — create one with last_number = 1
        prefix = _resolve_prefix(db, company_id, document_type, prefix_override)
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
            return f"{prefix}/{fiscal_year}/00001"
        except IntegrityError:
            # Step 3: Another transaction created it between our UPDATE and INSERT.
            # Expunge the failed object and retry the atomic increment.
            db.rollback()
            logger.warning(f"Sequence creation race for {document_type}/{fiscal_year}, retrying atomic increment")

            result = db.execute(
                update(DocumentSequence)
                .where(
                    DocumentSequence.company_id == company_id,
                    DocumentSequence.document_type == document_type,
                    DocumentSequence.fiscal_year == fiscal_year
                )
                .values(last_number=DocumentSequence.last_number + 1)
            )

            seq = db.query(DocumentSequence).filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type,
                DocumentSequence.fiscal_year == fiscal_year
            ).first()

            if not seq:
                raise Exception(f"Failed to generate document number for {document_type}/{fiscal_year}")

            prefix = _resolve_prefix(db, company_id, document_type, prefix_override, seq)
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
