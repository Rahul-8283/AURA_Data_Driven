from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from app.db.supabase import supabase_client
from app.services.embeddings import embed_texts

TABLE = "literature_chunks"
MATCH_FUNCTION = "match_literature_chunks"
BATCH_SIZE = 100

# Metadata keys that are promoted to indexed columns; everything else stays in the metadata jsonb.
_COLUMN_KEYS = ("doi", "title_key", "graph_extracted")


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def _batches(items: Sequence, size: int = BATCH_SIZE) -> Iterator[Sequence]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


class LiteratureStore:
    """Literature chunks and their embeddings, kept in Supabase Postgres with pgvector.

    Uses the service-role client, so it bypasses row level security; the table has RLS on
    and no policies, which keeps it unreachable from the browser."""

    def __init__(self, client=None):
        self._client = client or supabase_client

    def _table(self):
        return self._client.table(TABLE)

    @staticmethod
    def _row(chunk_id: str, document: str, embedding: Sequence[float], metadata: Optional[Dict]) -> Dict:
        extras = dict(metadata or {})
        return {
            "id": chunk_id,
            "document": document,
            "embedding": vector_literal(embedding),
            "doi": extras.pop("doi", None) or None,
            "title_key": extras.pop("title_key", None) or None,
            "graph_extracted": bool(extras.pop("graph_extracted", False)),
            "metadata": extras,
        }

    def upsert_vectors(self, ids: List[str], documents: List[str], metadatas: List[Dict],
                       embeddings: List[List[float]]) -> None:
        rows = [self._row(i, d, e, m) for i, d, e, m in zip(ids, documents, embeddings, metadatas)]
        for batch in _batches(rows):
            self._table().upsert(list(batch), on_conflict="id").execute()

    def upsert(self, ids: List[str], documents: List[str], metadatas: List[Dict]) -> None:
        self.upsert_vectors(ids, documents, metadatas, embed_texts(documents))

    def count(self) -> int:
        response = self._table().select("id", count="exact", head=True).execute()
        return response.count or 0

    def count_pending(self, chunk_ids: Optional[Sequence[str]] = None) -> int:
        if chunk_ids is None:
            response = (self._table().select("id", count="exact", head=True)
                        .eq("graph_extracted", False).execute())
            return response.count or 0
        total = 0
        for batch in _batches(list(chunk_ids)):
            response = (self._table().select("id", count="exact", head=True)
                        .eq("graph_extracted", False).in_("id", list(batch)).execute())
            total += response.count or 0
        return total

    def fetch_pending(self, limit: int, chunk_ids: Optional[Sequence[str]] = None) -> List[Tuple[str, str]]:
        """Up to `limit` (id, document) pairs still awaiting graph extraction, oldest first."""
        if chunk_ids is None:
            response = (self._table().select("id, document").eq("graph_extracted", False)
                        .order("created_at").limit(limit).execute())
            return [(row["id"], row["document"]) for row in response.data]
        found: List[Tuple[str, str]] = []
        for batch in _batches(list(chunk_ids)):
            if len(found) >= limit:
                break
            response = (self._table().select("id, document").eq("graph_extracted", False)
                        .in_("id", list(batch)).order("created_at").execute())
            found.extend((row["id"], row["document"]) for row in response.data)
        return found[:limit]

    def mark_graph_extracted(self, ids: Iterable[str]) -> None:
        for batch in _batches(list(ids)):
            self._table().update({"graph_extracted": True}).in_("id", list(batch)).execute()

    def exists(self, doi: Optional[str] = None, title_key: Optional[str] = None) -> bool:
        if doi:
            response = self._table().select("id").eq("doi", doi).limit(1).execute()
            if response.data:
                return True
        if title_key:
            response = self._table().select("id").eq("title_key", title_key).limit(1).execute()
            return bool(response.data)
        return False

    def delete_by_doi(self, doi: str) -> None:
        self._table().delete().eq("doi", doi).execute()

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Nearest chunks by cosine distance. Returns content, metadata and distance per hit."""
        vector = embed_texts([query])[0]
        response = self._client.rpc(MATCH_FUNCTION, {
            "query_embedding": vector_literal(vector),
            "match_count": n_results,
        }).execute()
        return [
            {
                "content": row["document"],
                "metadata": row.get("metadata") or {},
                "distance": 1.0 - float(row["similarity"]),
            }
            for row in response.data
        ]

    def heartbeat(self) -> None:
        self._table().select("id").limit(1).execute()


_store: Optional[LiteratureStore] = None


def get_literature_store() -> LiteratureStore:
    global _store
    if _store is None:
        _store = LiteratureStore()
    return _store
