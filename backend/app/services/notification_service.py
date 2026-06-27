"""User notification service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import Notification
from app.repositories.misc_repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    async def create_notification(
        self,
        type: str,
        title: str,
        message: str,
        user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
    ) -> Notification:
        notification = Notification(
            type=type,
            title=title,
            message=message,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
            is_read=False,
        )
        return await self.repo.create(notification)

    async def list_unread(self, user_id: UUID | None = None) -> list[Notification]:
        return await self.repo.list_unread(user_id)

    async def mark_read(self, notification_id: UUID) -> Notification | None:
        notification = await self.repo.get_by_id(notification_id)
        if notification:
            notification.is_read = True
            return await self.repo.update(notification)
        return None
