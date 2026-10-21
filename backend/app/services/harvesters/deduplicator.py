import hashlib
import logging
import re
from typing import Optional
from app.db.literature_store import get_literature_store

logger = logging.getLogger(__name__)


def title_key(title: str) -> str:
    """Case, punctuation and whitespace insensitive fingerprint of a title.

    The same paper arrives from different sources under different identifiers
    (arxiv:..., doi:..., pubmed:...), so the DOI alone cannot detect it.
    """
    normalized = re.sub(r"[^a-z0-9]+", "", title.lower())
    return hashlib.sha1(normalized.encode()).hexdigest()[:16] if normalized else ""


class LiteratureDeduplicator:
    def __init__(self, store=None):
        self._store = store

    @property
    def store(self):
        if self._store is None:
            self._store = get_literature_store()
        return self._store

    def is_already_indexed(self, doi: str, title: Optional[str] = None) -> bool:
        """Check pgvector for this identifier, or for the same title from another source."""
        try:
            if doi and self.store.exists(doi=doi):
                return True
            key = title_key(title) if title else ""
            return bool(key) and self.store.exists(title_key=key)
        except Exception as e:
            logger.debug(f"Deduplication lookup failed: {e}")
            return False
