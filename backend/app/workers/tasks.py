"""Celery background tasks for AI and pipeline operations."""

import asyncio
import logging
from uuid import UUID

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in sync Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _process_email_async(email_id: str) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.pipeline_service import PipelineService

    async with AsyncSessionLocal() as session:
        try:
            service = PipelineService(session)
            result = await service.process_email(UUID(email_id))
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def _process_all_pending_async() -> dict:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.base import EmailStatus
    from app.models.email import Email
    from app.services.pipeline_service import PipelineService

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Email).where(Email.status == EmailStatus.RECEIVED.value).limit(50)
        )
        emails = list(result.scalars().all())
        service = PipelineService(session)
        processed = []
        for email in emails:
            try:
                r = await service.process_email(email.id)
                processed.append({"email_id": str(email.id), "outcome": r.get("outcome")})
            except Exception as exc:
                logger.exception("Failed to process email %s", email.id)
                processed.append({"email_id": str(email.id), "error": str(exc)})
        await session.commit()
        return {"processed": len(processed), "results": processed}


async def _sync_gmail_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.gmail_service import GmailService

    async with AsyncSessionLocal() as session:
        service = GmailService(session)
        result = await service.sync_emails()
        await session.commit()
        return result


async def _analytics_snapshot_async() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.analytics_service import AnalyticsService

    async with AsyncSessionLocal() as session:
        service = AnalyticsService(session)
        snapshot = await service.save_snapshot()
        await session.commit()
        return {"snapshot_id": str(snapshot.id)}


@celery_app.task(name="app.workers.tasks.process_email_task", bind=True, max_retries=3)
def process_email_task(self, email_id: str) -> dict:
    try:
        return _run_async(_process_email_async(email_id))
    except Exception as exc:
        logger.exception("Pipeline task failed for email %s", email_id)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.tasks.process_all_pending_task")
def process_all_pending_task() -> dict:
    return _run_async(_process_all_pending_async())


@celery_app.task(name="app.workers.tasks.sync_gmail_task")
def sync_gmail_task() -> dict:
    return _run_async(_sync_gmail_async())


@celery_app.task(name="app.workers.tasks.run_analytics_snapshot_task")
def run_analytics_snapshot_task() -> dict:
    return _run_async(_analytics_snapshot_async())
