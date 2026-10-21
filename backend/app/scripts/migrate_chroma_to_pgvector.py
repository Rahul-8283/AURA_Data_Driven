"""One-time copy of a local ChromaDB collection into the pgvector literature store.

chromadb is not a project dependency, so provide it for this command only:
    uv run --with chromadb python -m app.scripts.migrate_chroma_to_pgvector --path ./chroma_data

Stored embeddings are copied as they are, not recomputed. Rows are upserted by id, so re-running
the migration is safe. Use --dry-run to count what would be copied without writing anything.
"""
import argparse
import sys
from typing import Dict, List, Sequence

from app.services.embeddings import EMBEDDING_DIM

PAGE_SIZE = 500


def to_store_arguments(ids: Sequence[str], documents: Sequence[str], metadatas: Sequence,
                       embeddings: Sequence) -> Dict[str, List]:
    """Shapes one page of Chroma output into the arguments of LiteratureStore.upsert_vectors."""
    vectors = [[float(x) for x in embedding] for embedding in embeddings]
    for chunk_id, vector in zip(ids, vectors):
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"chunk {chunk_id} has {len(vector)} dimensions, expected {EMBEDDING_DIM}")
    return {
        "ids": list(ids),
        "documents": list(documents),
        "metadatas": [dict(meta or {}) for meta in metadatas],
        "embeddings": vectors,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Copy a ChromaDB collection into pgvector.")
    parser.add_argument("--path", required=True, help="Chroma PersistentClient directory, e.g. ./chroma_data")
    parser.add_argument("--collection", default="battery_literature")
    parser.add_argument("--dry-run", action="store_true", help="Count rows and check dimensions without writing")
    args = parser.parse_args(argv)

    import chromadb  # imported here so the rest of the project never needs it

    collection = chromadb.PersistentClient(path=args.path).get_collection(name=args.collection)
    total = collection.count()
    print(f"Collection '{args.collection}' at {args.path}: {total} chunks")

    if args.dry_run:
        page = collection.get(limit=min(PAGE_SIZE, total), include=["embeddings"]) if total else None
        if page is not None:
            to_store_arguments(page["ids"], [""] * len(page["ids"]), [{}] * len(page["ids"]), page["embeddings"])
        print("Dry run: nothing written.")
        return 0

    from app.db.literature_store import get_literature_store
    store = get_literature_store()
    migrated = 0
    for offset in range(0, total, PAGE_SIZE):
        page = collection.get(limit=PAGE_SIZE, offset=offset,
                              include=["documents", "metadatas", "embeddings"])
        store.upsert_vectors(**to_store_arguments(page["ids"], page["documents"],
                                                  page["metadatas"], page["embeddings"]))
        migrated += len(page["ids"])
        print(f"  copied {migrated}/{total}")

    print(f"Done: {migrated} chunks in pgvector (store now holds {store.count()}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
