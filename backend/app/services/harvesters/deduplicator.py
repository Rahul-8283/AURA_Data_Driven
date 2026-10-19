import logging
from typing import Optional
from app.db.chroma_client import init_literature_collection

logger = logging.getLogger(__name__)

class LiteratureDeduplicator:
    def __init__(self, collection=None):
        self._collection = collection

    @property
    def collection(self):
        if self._collection is None:
            self._collection = init_literature_collection()
        return self._collection

    def is_already_indexed(self, doi: str, title: Optional[str] = None) -> bool:
        """
        Check ChromaDB to verify whether this document DOI or title
        has already been embedded and stored.
        """
        if not doi:
            return False
        try:
            res = self.collection.get(where={"doi": doi}, limit=1)
            if res and res.get("ids") and len(res["ids"]) > 0:
                return True
        except Exception as e:
            logger.debug(f"Error checking deduplication by DOI: {e}")

        return False
