"""Runs the real ingestion tasks against an in-memory ChromaDB with real embeddings.

Harvesters and the LLM are faked, so it needs no network and spends no quota. It checks the
assumptions the unit tests' fake collection makes about Chroma itself. Usage (from backend/):
    .venv/bin/python -m app.scripts.verify_ingestion_pipeline
"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import chromadb

from app.models.graph import Triplet
from app.services.embeddings import get_huggingface_embedding_function
from app.services.harvesters import HarvestedDocument
from worker.tasks import harvest_and_ingest_task, process_chroma_chunks_task

failures = []


def check(label: str, condition: bool) -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


def doc(title, doi, source):
    summary = f"{title}. A layered oxide cathode for lithium-ion batteries with improved capacity retention and cycle life."
    return HarvestedDocument(title=title, summary=summary, doi=doi, source=source)


def harvester(docs):
    class _H:
        async def harvest(self, query, max_results=10):
            return list(docs)
    return _H


def run_harvest(collection, per_source):
    patches = {f"{name}Harvester": harvester(per_source.get(name.lower(), [])) for name in ("Arxiv", "Wikipedia", "Crossref", "PubMed")}
    with patch.multiple("worker.tasks", **patches), \
         patch("worker.tasks.init_literature_collection", return_value=collection), \
         patch.object(process_chroma_chunks_task, "delay", return_value=SimpleNamespace(id="queued")) as delay:
        return harvest_and_ingest_task.run("cathode", ["all"], 10), delay


def run_extraction(collection, **kwargs):
    triplet = Triplet(subject_label="Material", subject="NMC811", predicate="CAN_BE_DOPED_WITH", object_label="Element", object="Mg")
    with patch("worker.tasks.init_literature_collection", return_value=collection), \
         patch("worker.tasks.extract_triplets_from_text", return_value=[triplet]) as extractor, \
         patch("worker.tasks.ingest_triplets"):
        result = process_chroma_chunks_task.run(**kwargs)
    return result, extractor


collection = chromadb.EphemeralClient().get_or_create_collection(
    name="battery_literature",
    embedding_function=get_huggingface_embedding_function(),
    metadata={"hnsw:space": "cosine"},
)

print("1. First harvest: duplicates across sources are indexed once")
paper_a = doc("Mg-doped NMC811 cathodes", "arxiv:1", "arxiv")
paper_a_again = doc("Mg doped NMC811 cathodes!", "doi:10.1/a", "crossref")
paper_b = doc("Cobalt-free layered oxides", "pubmed:2", "pubmed")
result, delay = run_harvest(collection, {"arxiv": [paper_a], "crossref": [paper_a_again], "pubmed": [paper_b]})
stored = collection.get(include=["metadatas"])
check("two distinct papers indexed", result["new_papers_indexed"] == 2)
check("chunks stored in Chroma match the ids queued for extraction", sorted(stored["ids"]) == sorted(delay.call_args.kwargs["chunk_ids"]))
check("new chunks are flagged graph_extracted=False", all(m["graph_extracted"] is False for m in stored["metadatas"]))
check("title fingerprint stored", all(m["title_key"] for m in stored["metadatas"]))

print("2. Second harvest of the same papers")
result, delay = run_harvest(collection, {"arxiv": [paper_a], "crossref": [paper_a_again], "pubmed": [paper_b]})
check("nothing new indexed (DOI and cross-source title dedupe against the real index)", result["new_papers_indexed"] == 0)
check("no extraction queued", delay.call_count == 0)

print("3. Extraction restricted to the new chunks")
chunk_ids = stored["ids"]
result, extractor = run_extraction(collection, chunk_ids=chunk_ids)
after = collection.get(include=["metadatas"])
check("every chunk now flagged graph_extracted=True", all(m["graph_extracted"] is True for m in after["metadatas"]))
check("the update kept the other metadata keys", all({"title", "doi", "source", "title_key"} <= set(m) for m in after["metadatas"]))
check("result reports nothing pending", result["chunks_pending"] == 0 and result["chunks_extracted"] == len(chunk_ids))

print("4. A legacy chunk without the flag is picked up, finished chunks are not")
collection.upsert(documents=["legacy chunk about spinel cathodes"], metadatas=[{"source": "legacy.pdf"}], ids=["legacy-1"])
result, extractor = run_extraction(collection)
check("exactly one extraction call", extractor.call_count == 1)
check("only the legacy chunk was sent", extractor.call_args.args[0] == "legacy chunk about spinel cathodes")
check("legacy chunk is now flagged", collection.get(ids=["legacy-1"], include=["metadatas"])["metadatas"][0]["graph_extracted"] is True)

print("5. Nothing left to do")
result, extractor = run_extraction(collection)
check("no LLM call when everything is extracted", extractor.call_count == 0 and result["chunks_pending"] == 0)

print("\nFAILED: " + ", ".join(failures) if failures else "\nAll checks passed.")
sys.exit(1 if failures else 0)
