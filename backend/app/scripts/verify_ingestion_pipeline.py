"""Runs the real ingestion tasks against the live pgvector store, with fake sources and a fake LLM.

Harvesters, the LLM and Neo4j are replaced, so no quota is spent and nothing is written to the graph.
Every row it writes has a DOI under a fresh "verify-" prefix, and those rows are deleted at the end.
Needs the Supabase schema applied. Usage (from backend/):
    uv run python -m app.scripts.verify_ingestion_pipeline
"""
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.db.literature_store import get_literature_store
from app.services.harvesters import HarvestedDocument
from worker.tasks import extract_graph_triplets_task, harvest_and_ingest_task

failures = []


def check(label: str, condition: bool) -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


def summary(title: str, doi: str, source: str, run: str) -> HarvestedDocument:
    body = (f"{title}: a layered oxide cathode study reporting capacity retention and cycle life "
            f"for lithium-ion batteries ({run}).")
    return HarvestedDocument(title=title, summary=body, doi=doi, source=source)


def harvester(docs):
    class _Harvester:
        async def harvest(self, query, max_results=10):
            return list(docs)
    return _Harvester


def run_harvest(per_source, run):
    patches = {f"{name}Harvester": harvester(per_source.get(name.lower(), []))
               for name in ("Arxiv", "Wikipedia", "Crossref", "PubMed")}
    with patch.multiple("worker.tasks", **patches), \
         patch.object(extract_graph_triplets_task, "delay", return_value=SimpleNamespace(id="queued")) as delay:
        result = harvest_and_ingest_task.run(f"cathode {run}", ["all"], 10)
    return result, delay


def main() -> int:
    run = uuid.uuid4().hex[:8]
    store = get_literature_store()
    dois = [f"verify-{run}:arxiv:1", f"verify-{run}:pubmed:2", f"verify-{run}:crossref:3"]
    try:
        print("1. First harvest")
        papers = {
            "arxiv": [summary(f"Mg-doped NMC811 cathodes {run}", dois[0], "arxiv", run)],
            "crossref": [summary(f"Mg doped NMC811 cathodes {run}!", dois[2], "crossref", run)],
            "pubmed": [summary(f"Cobalt-free layered oxides {run}", dois[1], "pubmed", run)],
        }
        result, delay = run_harvest(papers, run)
        check("two distinct papers indexed (cross-source duplicate skipped)", result["new_papers_indexed"] == 2)
        check("chunks written to pgvector", result["chunks_indexed"] >= 2 and store.exists(doi=dois[0]))
        queued = delay.call_args.kwargs["chunk_ids"] if delay.call_args else []
        check("extraction queued for exactly the new chunks", len(queued) == result["chunks_indexed"] and queued)
        check("new chunks are pending graph extraction", store.count_pending(queued) == len(queued))

        print("2. Second harvest of the same papers")
        result, delay = run_harvest(papers, run)
        check("nothing new indexed", result["new_papers_indexed"] == 0)
        check("no extraction queued", delay.call_count == 0)

        print("3. Graph extraction over the new chunks only")
        with patch("worker.tasks.extract_triplets_from_text", return_value=[]) as extractor, \
             patch("worker.tasks.ingest_triplets") as ingester:
            extraction = extract_graph_triplets_task.run(chunk_ids=queued)
        check("LLM called once per group of chunks", extractor.call_count >= 1)
        check("nothing ingested when the LLM found no triplets", ingester.call_count == 0)
        check("every queued chunk marked extracted", store.count_pending(queued) == 0)
        check("result reports nothing pending in scope", extraction["chunks_pending"] == 0)

        print("4. Extraction with nothing pending is a no-op")
        with patch("worker.tasks.extract_triplets_from_text") as extractor:
            idle = extract_graph_triplets_task.run(chunk_ids=queued)
        check("no LLM call when everything is extracted", extractor.call_count == 0 and idle["chunks_extracted"] == 0)
    finally:
        for doi in dois:
            try:
                store.delete_by_doi(doi)
            except Exception:
                pass

    check("verify rows removed", not any(store.exists(doi=d) for d in dois))
    print("\nFAILED: " + ", ".join(failures) if failures else "\nAll ingestion pipeline checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
