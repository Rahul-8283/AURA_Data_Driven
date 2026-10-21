import logging
import ssl
from datetime import datetime, timezone
from typing import Optional, Tuple

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_TTL_SECONDS = 2 * 24 * 60 * 60


def _build_client() -> redis.Redis:
    kwargs = {"socket_connect_timeout": 3, "socket_timeout": 3}
    if settings.REDIS_URL.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
    return redis.Redis.from_url(settings.REDIS_URL, **kwargs)


class DailyLimiter:
    """Per-user counter that resets each UTC day, kept in Redis so every API process shares it.

    Fails open: if Redis cannot be reached the request is allowed, because a Redis outage should
    not take chat down. The LLM quota is the backstop in that case."""

    def __init__(self, client: Optional[redis.Redis] = None):
        self._client = client

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = _build_client()
        return self._client

    @staticmethod
    def key(user_id: str, now: Optional[datetime] = None) -> str:
        day = (now or datetime.now(timezone.utc)).strftime("%Y%m%d")
        return f"aura:ask:{user_id}:{day}"

    def consume(self, user_id: str, limit: int) -> Tuple[bool, Optional[int]]:
        """Counts one use. Returns (allowed, remaining); remaining is None when Redis is unavailable."""
        try:
            key = self.key(user_id)
            count = int(self.client.incr(key))
            if count == 1:
                self.client.expire(key, _TTL_SECONDS)
            return count <= limit, max(limit - count, 0)
        except Exception as e:
            logger.warning("Daily limit check unavailable (%s); allowing the request", type(e).__name__)
            return True, None


daily_limiter = DailyLimiter()
