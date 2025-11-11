"""Celery application configuration."""

from celery import Celery

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "socratic-backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.autodiscover_tasks(["app.tasks"])
