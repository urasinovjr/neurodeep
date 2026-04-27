import os

from celery import Celery

celery_app = Celery(
    "psychograph",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
)

celery_app.conf.update(
    task_default_queue="psychograph",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
