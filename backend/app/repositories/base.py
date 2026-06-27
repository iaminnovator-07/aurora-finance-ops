"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def create(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        try:
            from app.services.firestore_sync_service import sync_entity_to_firestore
            await sync_entity_to_firestore(entity, "create")
        except Exception:
            pass
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        await self.session.flush()
        await self.session.refresh(entity)
        try:
            from app.services.firestore_sync_service import sync_entity_to_firestore
            await sync_entity_to_firestore(entity, "update")
        except Exception:
            pass
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
