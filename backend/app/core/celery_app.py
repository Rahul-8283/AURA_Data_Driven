import sys
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
    include=['worker.tasks'],
    # Keep Celery 5.x's default "retry connecting at startup" behavior
    # explicit, since Celery 6 changes what broker_connection_retry means.
    broker_connection_retry_on_startup=True,
)

if sys.platform == "darwin":
    # macOS's multiprocessing defaults to the "spawn" start method, which
    # doesn't inherit Celery's task registry into prefork worker child
    # processes and causes "ValueError: not enough values to unpack
    # (expected 3, got 0)" in fast_trace_task as soon as a task is received.
    # The solo pool runs tasks in-process and sidesteps this entirely.
    # Linux (production) deployments are unaffected and keep the faster
    # prefork pool.
    celery_app.conf.worker_pool = "solo"

# Managed Redis providers (e.g. Upstash) expose a TLS endpoint via the
# rediss:// scheme. Configuring SSL through broker_use_ssl/redis_backend_use_ssl
# is more reliable across kombu/redis-py versions than relying on
# ssl_cert_reqs query-string parsing, which only accepts lowercase values
# ("none"/"optional"/"required") and silently breaks otherwise.
if settings.REDIS_URL.startswith("rediss://"):
    ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.broker_use_ssl = ssl_opts
    celery_app.conf.redis_backend_use_ssl = ssl_opts
