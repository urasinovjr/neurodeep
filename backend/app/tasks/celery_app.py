from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "psychograph",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL,
)

celery_app.conf.update(
    task_default_queue="psychograph",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
