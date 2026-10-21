import hashlib
import logging
import re
from typing import Optional
from app.db.chroma_client import init_literature_collection

logger = logging.getLogger(__name__)


def title_key(title: str) -> str:
    """Case, punctuation and whitespace insensitive fingerprint of a title.

    The same paper arrives from different sources under different identifiers
    (arxiv:..., doi:..., pubmed:...), so the DOI alone cannot detect it.
    """
    normalized = re.sub(r"[^a-z0-9]+", "", title.lower())
    return hashlib.sha1(normalized.encode()).hexdigest()[:16] if normalized else ""


class LiteratureDeduplicator:
    def __init__(self, collection=None):
        self._collection = collection

    @property
    def collection(self):
        if self._collection is None:
            self._collection = init_literature_collection()
        return self._collection

    def _exists(self, where: dict) -> bool:
        try:
            res = self.collection.get(where=where, limit=1)
            return bool(res and res.get("ids"))
        except Exception as e:
            logger.debug(f"Deduplication lookup failed for {where}: {e}")
            return False

    def is_already_indexed(self, doi: str, title: Optional[str] = None) -> bool:
        """Check ChromaDB for this identifier, or for the same title from another source."""
        if doi and self._exists({"doi": doi}):
            return True
        key = title_key(title) if title else ""
        return bool(key) and self._exists({"title_key": key})
