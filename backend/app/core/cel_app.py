from celery import Celery
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Optional configuration overrides
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.workers"])
