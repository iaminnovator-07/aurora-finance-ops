"""Celery application configuration."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aurora_tia",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "app.workers.tasks.process_email_task": {"queue": "pipeline"},
        "app.workers.tasks.process_all_pending_task": {"queue": "pipeline"},
        "app.workers.tasks.sync_gmail_task": {"queue": "mail"},
        "app.workers.tasks.run_analytics_snapshot_task": {"queue": "analytics"},
    },
)
