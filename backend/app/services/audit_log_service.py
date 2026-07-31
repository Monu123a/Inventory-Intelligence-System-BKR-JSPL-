from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.schema import AuditLog


class AuditLogService:
    @staticmethod
    def log(
        db: Session,
        *,
        company_id: int,
        entity_type: str,
        entity_id: int,
        event_type: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        entry = AuditLog(
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            message=message,
            metadata_payload=metadata or {},
        )
        db.add(entry)
        db.flush()
        return entry
