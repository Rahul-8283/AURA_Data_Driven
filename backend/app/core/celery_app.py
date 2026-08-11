from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "aura_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure serialization
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    include=['worker.tasks']
)
