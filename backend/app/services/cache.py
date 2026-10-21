import time
from collections import OrderedDict
from collections.abc import MutableMapping
from typing import Callable, Iterator, List

from app.core.config import settings


class TTLCache(MutableMapping):
    """Bounded, expiring mapping: least-recently-used entries are evicted past max_entries and
    entries older than ttl_seconds disappear. Both bounds matter for LLM results derived from a
    knowledge base that keeps changing as literature is ingested."""

    def __init__(self, max_entries: int, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: "OrderedDict[object, tuple[float, object]]" = OrderedDict()

    def _purge_expired(self) -> None:
        now = self._clock()
        for key in [k for k, (stored_at, _) in self._items.items() if now - stored_at >= self._ttl]:
            del self._items[key]

    def __getitem__(self, key):
        self._purge_expired()
        stored_at, value = self._items[key]
        self._items.move_to_end(key)
        return value

    def __setitem__(self, key, value) -> None:
        self._items[key] = (self._clock(), value)
        self._items.move_to_end(key)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)

    def __delitem__(self, key) -> None:
        del self._items[key]

    def __iter__(self) -> Iterator:
        self._purge_expired()
        return iter(list(self._items))

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()


_llm_caches: List[TTLCache] = []


def llm_cache() -> TTLCache:
    """A cache for LLM-derived results, sized and expired from settings and registered so
    clear_llm_caches() can drop it when the knowledge base changes."""
    cache = TTLCache(max_entries=settings.LLM_CACHE_MAX_ENTRIES, ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)
    _llm_caches.append(cache)
    return cache


def clear_llm_caches() -> None:
    """Called after ingestion adds literature or graph facts, so cached predictions and validity
    verdicts made against the old knowledge are not reused. Clears this process only; other worker
    processes rely on the TTL."""
    for cache in _llm_caches:
        cache.clear()
