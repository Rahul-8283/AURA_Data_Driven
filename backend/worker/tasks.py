from app.core.celery_app import celery_app
from app.agents.workflow import app_graph, recursion_limit
from app.agents.state import init_research_state
import asyncio
import time
import logging
from app.core.config import settings
from app.db.literature_store import get_literature_store
from app.db.supabase import supabase_client
from app.services.cache import clear_llm_caches
from app.services.graph.extractor import extract_triplets_from_text
from app.services.graph.ingestion import ingest_triplets
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError
from app.services.harvesters import (
    HARVESTER_SOURCES,
    ArxivHarvester,
    CrossrefHarvester,
    HarvesterError,
    LiteratureDeduplicator,
    PubMedHarvester,
    WikipediaHarvester,
    title_key,
)
from app.services.ingestion.chunker import get_chunker
from app.services.ingestion.upsert import process_and_upsert

logger = logging.getLogger(__name__)

def mark_task_failed(task_id: str, error: Exception) -> None:
    message = str(error) if isinstance(error, LLMUnavailableError) else f"Discovery run failed ({type(error).__name__})."
    try:
        supabase_client.table("ResearchTasks").update({
            "status": "failed",
            "result_json": {"error": message},
        }).eq("id", task_id).execute()
    except Exception as e:
        logger.error(f"Could not mark task {task_id} as failed: {e}")

@celery_app.task(bind=True, name="test_dummy_task")
def test_dummy_task(self, iterations: int):
    for i in range(iterations):
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'current': i, 'total': iterations})
    return {"status": "Complete", "result": f"Processed {iterations} items."}

MAX_CONSECUTIVE_EXTRACTION_FAILURES = 3


def _safe_update_state(task_self, state: str, meta: dict):
    if task_self and getattr(task_self, "request", None) and getattr(task_self.request, "id", None):
        try:
            task_self.update_state(state=state, meta=meta)
        except Exception as e:
            logger.debug(f"Could not update task state: {e}")


@celery_app.task(bind=True, name="extract_graph_triplets")
def extract_graph_triplets_task(self, chunk_ids: list = None):
    """
    Mines literature chunks that have not been through triplet extraction yet and ingests the
    validated triplets into Neo4j. Chunks go to the LLM in groups, and one run spends at most
    GRAPH_EXTRACTION_MAX_CALLS requests, so it cannot exhaust the daily quota shared with discovery
    runs; whatever is left stays pending for the next run. Pass chunk_ids to restrict a run to
    freshly indexed chunks. Stops early, without marking anything it did not finish, when the quota
    is spent, the providers keep failing, or Neo4j rejects a write.
    """
    store = get_literature_store()
    group_size = max(1, settings.GRAPH_EXTRACTION_GROUP_SIZE)
    max_groups = max(1, settings.GRAPH_EXTRACTION_MAX_CALLS)

    total_pending = store.count_pending(chunk_ids)
    rows = store.fetch_pending(group_size * max_groups, chunk_ids)
    groups = [rows[i:i + group_size] for i in range(0, len(rows), group_size)]

    chunks_extracted = 0
    triplets_ingested = 0
    consecutive_failures = 0
    stopped_reason = None

    for group_number, group in enumerate(groups, start=1):
        group_ids = [chunk_id for chunk_id, _ in group]
        try:
            triplets = extract_triplets_from_text("\n\n".join(document for _, document in group))
        except LLMQuotaExceeded:
            stopped_reason = "quota_exhausted"
            logger.warning("Triplet extraction stopped: LLM quota exhausted. Remaining chunks stay pending.")
            break
        except LLMUnavailableError:
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_EXTRACTION_FAILURES:
                stopped_reason = "llm_unavailable"
                break
            continue
        consecutive_failures = 0

        if triplets:
            try:
                ingest_triplets([t.model_dump() for t in triplets])
            except Exception as e:
                stopped_reason = "neo4j_error"
                logger.error(f"Triplet ingestion failed ({type(e).__name__}); stopping extraction run.")
                break

        store.mark_graph_extracted(group_ids)
        chunks_extracted += len(group_ids)
        triplets_ingested += len(triplets)
        _safe_update_state(self, "PROGRESS", {
            "stage": "extracting_triplets",
            "message": f"Extracted {triplets_ingested} triplets from {chunks_extracted} chunks...",
            "triplets_ingested": triplets_ingested,
            "current": group_number,
            "total": len(groups),
        })

    if triplets_ingested:
        clear_llm_caches()

    chunks_pending = total_pending - chunks_extracted
    message = f"Extracted {triplets_ingested} triplets from {chunks_extracted} chunks; {chunks_pending} chunks still pending."
    if stopped_reason:
        message += f" Stopped early: {stopped_reason}."
    return {
        "status": "Complete",
        "chunks_extracted": chunks_extracted,
        "chunks_pending": chunks_pending,
        "triplets_ingested": triplets_ingested,
        "stopped_reason": stopped_reason,
        "message": message,
    }


@celery_app.task(bind=True, name="run_discovery_loop")
def run_discovery_loop(self, user_prompt: str, task_id: str, user_id: str = "default_user"):
    initial_state = init_research_state(task_id, user_prompt, user_id)

    async def _run():
        last_state = initial_state
        # planner + N x (mutator, predictor) + reporter exceeds LangGraph's default limit of 25
        config = {"recursion_limit": recursion_limit(settings.GA_GENERATIONS)}
        async for event in app_graph.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                last_state = state_update
                if node_name == "predictor":
                    gen = state_update.get("current_generation")
                    best_candidates = state_update.get("best_candidates", [])
                    best_score = best_candidates[0].get("fitness", 0) if best_candidates else 0

                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'message': f"Completed Generation {gen}...",
                            'generation': gen,
                            'best_score': round(best_score, 2)
                        }
                    )
        return last_state

    try:
        last_state = asyncio.run(_run())
    except Exception as e:
        mark_task_failed(task_id, e)
        raise
    return {
        "status": "success",
        "generation": last_state.get("current_generation", 0),
        "results": last_state.get("best_candidates", []),
        "executive_summary": last_state.get("final_summary", ""),
        "generation_history": last_state.get("generation_history", []),
    }


@celery_app.task(bind=True, name="harvest_and_ingest_task")
def harvest_and_ingest_task(self, query: str, sources: list = None, max_results: int = 10):
    """
    Harvests literature from the requested sources, drops off-topic and duplicate documents,
    chunks and embeds the rest into pgvector, then queues triplet extraction for just those new
    chunks. Fails when every source fails; a partial failure is reported in source_errors.
    """
    requested = list(sources or HARVESTER_SOURCES)
    active_sources = (
        list(HARVESTER_SOURCES) if "all" in requested
        else [name for name in dict.fromkeys(requested) if name in HARVESTER_SOURCES]
    )
    if not active_sources:
        raise ValueError("No valid literature sources requested.")

    _safe_update_state(self, state="PROGRESS", meta={
        "stage": "fetching",
        "message": f"Querying {', '.join(active_sources)} for '{query}'...",
        "papers_found": 0,
        "new_papers_indexed": 0,
    })

    harvester_classes = {
        "wikipedia": WikipediaHarvester,
        "arxiv": ArxivHarvester,
        "crossref": CrossrefHarvester,
        "pubmed": PubMedHarvester,
    }

    async def _fetch_all():
        documents = []
        errors = {}
        for source in active_sources:
            try:
                documents.extend(await harvester_classes[source]().harvest(query, max_results=max_results))
            except HarvesterError as ex:
                errors[source] = str(ex)
                logger.error(f"Harvester {source} failed: {ex}")
            except Exception as ex:
                errors[source] = f"{type(ex).__name__}"
                logger.exception(f"Harvester {source} crashed")
        return documents, errors

    all_docs, source_errors = asyncio.run(_fetch_all())
    if len(source_errors) == len(active_sources):
        raise HarvesterError(
            "All literature sources failed: " + "; ".join(f"{name}: {err}" for name, err in source_errors.items())
        )
    total_found = len(all_docs)

    _safe_update_state(self, state="PROGRESS", meta={
        "stage": "deduplicating",
        "message": f"Found {total_found} articles. Deduplicating against local index...",
        "papers_found": total_found,
        "new_papers_indexed": 0,
    })

    store = get_literature_store()
    dedup = LiteratureDeduplicator(store=store)
    chunker = get_chunker()

    seen = set()
    new_chunk_ids = []
    newly_indexed = 0
    for doc in all_docs:
        key = title_key(doc.title)
        if doc.doi in seen or (key and key in seen):
            continue  # same paper returned by two sources in this run
        seen.add(doc.doi)
        if key:
            seen.add(key)

        if dedup.is_already_indexed(doc.doi, doc.title):
            continue

        chunks = chunker.split_text(f"{doc.title}\n\n{doc.summary}")
        if not chunks:
            continue

        base_meta = {
            "title": doc.title,
            "title_key": key,
            "doi": doc.doi,
            "source": doc.source,
            "url": doc.url or "",
            "published_date": doc.published_date or "",
            "authors": ", ".join(doc.authors[:5]),
            "graph_extracted": False,
        }
        new_chunk_ids.extend(process_and_upsert(store, chunks, base_metadata=base_meta, doi=doc.doi))
        newly_indexed += 1

    extraction_task_id = None
    if new_chunk_ids:
        clear_llm_caches()
        extraction_task_id = extract_graph_triplets_task.delay(chunk_ids=new_chunk_ids).id

    message = f"Indexed {newly_indexed} new documents from {', '.join(s for s in active_sources if s not in source_errors)}."
    if extraction_task_id:
        message += f" Triplet extraction queued for {len(new_chunk_ids)} chunks."
    if source_errors:
        message += f" Sources failed: {', '.join(source_errors)}."

    return {
        "status": "Complete",
        "query": query,
        "sources": active_sources,
        "papers_found": total_found,
        "new_papers_indexed": newly_indexed,
        "chunks_indexed": len(new_chunk_ids),
        "source_errors": source_errors,
        "extraction_task_id": extraction_task_id,
        "message": message,
    }


@celery_app.task(bind=True, name="periodic_nightly_harvest")
def periodic_nightly_harvest(self):
    """
    Sweeps a fixed list of battery research topics. Only scheduled when NIGHTLY_HARVEST_ENABLED is
    set, and it fires only while a `celery beat` process is running.
    """
    topics = [
        "lithium-ion cathode degradation mechanisms",
        "solid-state electrolyte dendrite suppression",
        "cobalt-free high capacity cathode materials",
        "silicon anode solid electrolyte interphase",
        "sodium-ion battery cathode novel dopants"
    ]
    completed = 0
    failed = []
    for topic in topics:
        try:
            harvest_and_ingest_task.apply(args=[topic, ["arxiv", "crossref", "pubmed"], 5], throw=True)
            completed += 1
        except Exception as e:
            failed.append(topic)
            logger.error(f"Nightly harvest failed for topic '{topic}' ({type(e).__name__})")
    return {
        "status": "Complete" if not failed else "Partial",
        "topics_processed": completed,
        "topics_failed": len(failed),
    }
