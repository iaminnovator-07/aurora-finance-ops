from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import ApprovalQueue, BusinessRule, RuleEngineLog
from app.models.audit import AuditLog, Notification
from app.models.client import Client, ClientContact
from app.models.document import DocumentExtraction, TrustScore, VendorProfile
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Client)

    async def get_by_domain(self, domain: str) -> Client | None:
        result = await self.session.execute(select(Client).where(Client.domain == domain))
        return result.scalar_one_or_none()

    async def get_by_email_domain(self, email: str) -> Client | None:
        domain = email.split("@")[-1] if "@" in email else None
        if not domain:
            return None
        return await self.get_by_domain(domain)

    async def list_with_profiles(self, limit: int = 100) -> list[Client]:
        result = await self.session.execute(
            select(Client)
            .options(selectinload(Client.vendor_profile))
            .order_by(Client.name)
            .limit(limit)
        )
        return list(result.scalars().all())


class VendorProfileRepository(BaseRepository[VendorProfile]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, VendorProfile)

    async def get_by_client_id(self, client_id: UUID) -> VendorProfile | None:
        result = await self.session.execute(
            select(VendorProfile).where(VendorProfile.client_id == client_id)
        )
        return result.scalar_one_or_none()


class TrustScoreRepository(BaseRepository[TrustScore]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TrustScore)

    async def get_by_email_id(self, email_id: UUID) -> TrustScore | None:
        result = await self.session.execute(
            select(TrustScore).where(TrustScore.email_id == email_id)
        )
        return result.scalar_one_or_none()


class DocumentExtractionRepository(BaseRepository[DocumentExtraction]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DocumentExtraction)

    async def get_by_attachment_id(self, attachment_id: UUID) -> DocumentExtraction | None:
        result = await self.session.execute(
            select(DocumentExtraction).where(DocumentExtraction.attachment_id == attachment_id)
        )
        return result.scalar_one_or_none()


class ApprovalQueueRepository(BaseRepository[ApprovalQueue]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ApprovalQueue)

    async def list_by_status(self, status: str | None = None) -> list[ApprovalQueue]:
        query = select(ApprovalQueue).options(selectinload(ApprovalQueue.invoice))
        if status:
            query = query.where(ApprovalQueue.status == status)
        query = query.order_by(ApprovalQueue.priority.desc(), ApprovalQueue.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_invoice_id(self, invoice_id: UUID) -> ApprovalQueue | None:
        result = await self.session.execute(
            select(ApprovalQueue).where(ApprovalQueue.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()


class RuleEngineLogRepository(BaseRepository[RuleEngineLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, RuleEngineLog)

    async def get_by_invoice_id(self, invoice_id: UUID) -> list[RuleEngineLog]:
        result = await self.session.execute(
            select(RuleEngineLog).where(RuleEngineLog.invoice_id == invoice_id)
        )
        return list(result.scalars().all())


class BusinessRuleRepository(BaseRepository[BusinessRule]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BusinessRule)

    async def list_active(self) -> list[BusinessRule]:
        result = await self.session.execute(
            select(BusinessRule)
            .where(BusinessRule.is_active.is_(True))
            .order_by(BusinessRule.priority.desc())
        )
        return list(result.scalars().all())


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def list_by_entity(self, entity_type: str, entity_id: str) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_log(self, **kwargs) -> AuditLog:
        log = AuditLog(**kwargs)
        return await self.create(log)


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def list_unread(self, user_id: UUID | None = None) -> list[Notification]:
        query = select(Notification).where(Notification.is_read.is_(False))
        if user_id:
            query = query.where(Notification.user_id == user_id)
        result = await self.session.execute(query.order_by(Notification.created_at.desc()))
        return list(result.scalars().all())
