from celery import Celery

from .config import settings

celery_app = Celery(
    "cosselect",
    broker=settings.broker,
    backend=settings.backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

# Ensure tasks are registered when the worker imports this module.
celery_app.autodiscover_tasks(["app"])

from . import tasks  # noqa: E402,F401
