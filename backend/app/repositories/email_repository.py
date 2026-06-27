from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.email import Email, EmailAttachment
from app.repositories.base import BaseRepository


class EmailRepository(BaseRepository[Email]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Email)

    async def get_with_details(self, email_id: UUID) -> Email | None:
        result = await self.session.execute(
            select(Email)
            .options(selectinload(Email.attachments), selectinload(Email.trust_score))
            .where(Email.id == email_id)
        )
        return result.scalar_one_or_none()

    async def list_emails(
        self,
        *,
        unread_only: bool = False,
        flagged_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Email], int]:
        query = select(Email).options(selectinload(Email.attachments))
        count_query = select(func.count()).select_from(Email)

        if unread_only:
            query = query.where(Email.is_read.is_(False))
            count_query = count_query.where(Email.is_read.is_(False))
        if flagged_only:
            query = query.where(Email.is_flagged.is_(True))
            count_query = count_query.where(Email.is_flagged.is_(True))

        query = query.order_by(Email.received_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return list(result.scalars().all()), count_result.scalar_one()

    async def get_by_gmail_id(self, gmail_message_id: str) -> Email | None:
        result = await self.session.execute(
            select(Email).where(Email.gmail_message_id == gmail_message_id)
        )
        return result.scalar_one_or_none()

    async def find_duplicates(self, subject: str, from_email: str, days: int = 30) -> list[Email]:
        cutoff = datetime.utcnow()
        result = await self.session.execute(
            select(Email).where(
                Email.from_email == from_email,
                Email.subject == subject,
            ).order_by(Email.received_at.desc()).limit(10)
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self.session.execute(
            select(Email.status, func.count()).group_by(Email.status)
        )
        return {row[0]: row[1] for row in result.all()}


class EmailAttachmentRepository(BaseRepository[EmailAttachment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailAttachment)

    async def get_by_email_id(self, email_id: UUID) -> list[EmailAttachment]:
        result = await self.session.execute(
            select(EmailAttachment).where(EmailAttachment.email_id == email_id)
        )
        return list(result.scalars().all())
