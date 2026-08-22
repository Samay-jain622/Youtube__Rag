"""Celery worker application."""

from celery import Celery

from src.utils.config import settings

celery_app = Celery(
    "youtube_rag",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["src.tools.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
