"""Audit logging service."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.misc_repository import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def log_action(
        self,
        user_id: UUID | None,
        action: str,
        module: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        details: str | None = None,
        confidence: float | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            details=details,
            confidence=confidence,
        )
        return await self.repo.create(log)
