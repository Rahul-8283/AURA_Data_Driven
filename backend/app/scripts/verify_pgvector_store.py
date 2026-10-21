"""Live check of the pgvector literature store, plus a Chroma-to-pgvector migration round trip.

Writes only rows whose DOI starts with a fresh "verify-" prefix, and deletes them at the end,
including when a check fails. It needs the Supabase schema applied and chromadb for the migration
step, so run it as:
    uv run --with chromadb python -m app.scripts.verify_pgvector_store
"""
import sys
import tempfile
import uuid

from app.db.literature_store import get_literature_store
from app.scripts.migrate_chroma_to_pgvector import main as migrate
from app.services.embeddings import embed_texts

failures = []


def check(label: str, condition: bool) -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


def main() -> int:
    run = uuid.uuid4().hex[:8]
    prefix = f"verify-{run}"
    store = get_literature_store()
    dois = [f"{prefix}:a", f"{prefix}:b", f"{prefix}:c"]
    ids = [f"{prefix}-chunk-{n}" for n in range(3)]
    texts = [
        "Mg doping suppresses cation mixing in layered NMC811 cathodes.",
        "Solid electrolyte interphase growth on silicon anodes limits cycle life.",
        "A recipe for sourdough bread with a long cold fermentation.",
    ]
    metas = [{"doi": d, "title_key": f"{prefix}-title-{n}", "source": "verify", "graph_extracted": False}
             for n, d in enumerate(dois)]

    try:
        print("1. Writes and counts")
        before = store.count()
        store.upsert(ids, texts, metas)
        check("three chunks added", store.count() == before + 3)
        store.upsert(ids[:1], ["Mg doping suppresses cation mixing in NMC811 cathodes (revised)."], metas[:1])
        check("re-upserting an id replaces it rather than duplicating", store.count() == before + 3)

        print("2. Exact-match lookups")
        check("exists by doi", store.exists(doi=dois[0]))
        check("exists by title fingerprint", store.exists(title_key=metas[1]["title_key"]))
        check("missing doi is not found", not store.exists(doi=f"{prefix}:missing"))
        check("empty identifiers never match", not store.exists(doi="", title_key=None))

        print("3. Vector search")
        hits = store.search("How does Mg doping affect cathode stability?", 3)
        check("returns the requested number of hits", len(hits) == 3)
        check("closest chunk is the Mg-doping text", hits[0]["content"].startswith("Mg doping") and hits[0]["metadata"].get("source") == "verify")
        check("distances are ordered ascending", [h["distance"] for h in hits] == sorted(h["distance"] for h in hits))
        check("distances are cosine distances in [0, 2]", all(0 <= h["distance"] <= 2 for h in hits))

        print("4. Graph-extraction bookkeeping")
        check("three pending within this run's ids", store.count_pending(ids) == 3)
        pending = store.fetch_pending(2, chunk_ids=ids)
        check("fetch respects the limit and scope", len(pending) == 2 and all(cid in ids for cid, _ in pending))
        store.mark_graph_extracted([ids[0]])
        check("marked chunk leaves the pending set", store.count_pending(ids) == 2)
        check("unscoped pending count includes this run's chunks", store.count_pending() >= 2)

        print("5. Migration from a Chroma collection (embeddings copied, not recomputed)")
        import chromadb
        temp = tempfile.mkdtemp(prefix="verify-chroma-")
        migrated_ids = [f"{prefix}-legacy-{n}" for n in range(2)]
        migrated_texts = ["Cobalt-free LiNi0.5Mn0.5O2 delivers high capacity at 4.3 V.",
                          "Lithium dendrite growth through ceramic electrolytes."]
        legacy_dois = [f"{prefix}:legacy-{n}" for n in range(2)]
        collection = chromadb.PersistentClient(path=temp).create_collection("battery_literature")
        collection.add(ids=migrated_ids, documents=migrated_texts,
                       metadatas=[{"doi": d, "source": "legacy"} for d in legacy_dois],
                       embeddings=embed_texts(migrated_texts))
        dry = migrate(["--path", temp, "--dry-run"])
        check("dry run succeeds", dry == 0)
        check("dry run writes nothing", not store.exists(doi=legacy_dois[0]))
        done = migrate(["--path", temp])
        check("migration succeeds", done == 0)
        check("migrated rows carry their doi", store.exists(doi=legacy_dois[0]) and store.exists(doi=legacy_dois[1]))
        again = migrate(["--path", temp])
        check("re-running the migration is idempotent", again == 0 and store.exists(doi=legacy_dois[1]))
        top = store.search(migrated_texts[1], 1)[0]
        check("migrated vectors still find their own text", top["content"] == migrated_texts[1] and top["distance"] < 0.01)

        print("6. Cleanup")
        for doi in dois + legacy_dois:
            store.delete_by_doi(doi)
    finally:
        for doi in dois + [f"{prefix}:legacy-{n}" for n in range(2)]:
            try:
                store.delete_by_doi(doi)
            except Exception:
                pass

    check("no verify rows left behind", not store.exists(doi=dois[0]) and not store.exists(doi=f"{prefix}:legacy-0"))
    print("\nFAILED: " + ", ".join(failures) if failures else "\nAll pgvector checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
