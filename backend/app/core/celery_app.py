import ssl

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

# Managed Redis providers (e.g. Upstash) expose a TLS endpoint via the
# rediss:// scheme. Configuring SSL through broker_use_ssl/redis_backend_use_ssl
# is more reliable across kombu/redis-py versions than relying on
# ssl_cert_reqs query-string parsing, which only accepts lowercase values
# ("none"/"optional"/"required") and silently breaks otherwise.
if settings.REDIS_URL.startswith("rediss://"):
    ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.broker_use_ssl = ssl_opts
    celery_app.conf.redis_backend_use_ssl = ssl_opts
