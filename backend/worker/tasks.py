from app.core.celery_app import celery_app
from app.agents.workflow import app_graph
from app.agents.state import init_research_state
import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.chroma_client import init_literature_collection
from app.db.supabase import supabase_client
from app.services.graph.extractor import extract_triplets_from_text
from app.services.graph.ingestion import ingest_triplets
from app.services.llm.errors import LLMUnavailableError
from app.services.harvesters import (
    ArxivHarvester,
    CrossrefHarvester,
    LiteratureDeduplicator,
    PubMedHarvester,
    WikipediaHarvester,
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

@celery_app.task(bind=True, name="process_chroma_chunks")
def process_chroma_chunks_task(self):
    """
    Background task that iterates through text chunks stored in ChromaDB,
    passes them to the LLM extraction service concurrently, and ingests
    the validated triplets into Neo4j.
    """
    collection = init_literature_collection()
    
    # Fetch all documents from the collection
    results = collection.get(include=["documents"])
    documents = results.get("documents", [])
    
    if not documents:
        logger.warning("No documents found in ChromaDB collection to process.")
        return {"status": "Complete", "processed": 0, "triplets_ingested": 0}

    total_docs = len(documents)
    logger.info(f"Starting graph extraction for {total_docs} chunks...")
    
    total_triplets_ingested = 0
    processed_count = 0
    batch_size = 10
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i + batch_size]
        batch_triplets = []
        
        # Process batch concurrently
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_doc = {executor.submit(extract_triplets_from_text, doc): doc for doc in batch}
            for future in as_completed(future_to_doc):
                try:
                    triplets = future.result()
                    if triplets:
                        batch_triplets.extend([t.model_dump() for t in triplets])
                except Exception as e:
                    logger.error(f"Error extracting triplets for a chunk: {e}")
        
        # Ingest the batch into Neo4j
        if batch_triplets:
            try:
                ingest_triplets(batch_triplets)
                total_triplets_ingested += len(batch_triplets)
            except Exception as e:
                logger.error(f"Failed to ingest batch into Neo4j: {e}")
                
        processed_count += len(batch)
        self.update_state(state='PROGRESS', meta={'current': processed_count, 'total': total_docs})
        logger.info(f"Processed {processed_count}/{total_docs} chunks. Ingested {total_triplets_ingested} triplets so far.")

    return {
        "status": "Complete", 
        "processed_chunks": total_docs, 
        "total_triplets_ingested": total_triplets_ingested
    }


@celery_app.task(bind=True, name="run_discovery_loop")
def run_discovery_loop(self, user_prompt: str, task_id: str, user_id: str = "default_user"):
    initial_state = init_research_state(task_id, user_prompt, user_id)

    async def _run():
        last_state = initial_state
        # planner + 20 x (mutator, predictor) + reporter exceeds LangGraph's default limit of 25
        config = {"recursion_limit": 200}
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
    Asynchronous Celery task that harvests literature from Wikipedia, arXiv,
    Crossref, and PubMed, deduplicates, chunks, embeds into ChromaDB, and
    triggers Neo4j triplet extraction.
    """
    if not sources or "all" in sources:
        active_sources = ["arxiv", "wikipedia", "crossref", "pubmed"]
    else:
        active_sources = sources

    self.update_state(state="PROGRESS", meta={
        "stage": "fetching",
        "message": f"Querying {', '.join(active_sources)} for '{query}'...",
        "papers_found": 0,
        "new_papers_indexed": 0,
        "triplets_ingested": 0
    })

    harvesters_map = {
        "wikipedia": WikipediaHarvester(),
        "arxiv": ArxivHarvester(),
        "crossref": CrossrefHarvester(),
        "pubmed": PubMedHarvester(),
    }

    async def _fetch_all():
        all_docs = []
        for src_name in active_sources:
            h = harvesters_map.get(src_name)
            if h:
                try:
                    docs = await h.search(query, max_results=max_results)
                    all_docs.extend(docs)
                except Exception as ex:
                    logger.error(f"Harvester {src_name} failed: {ex}")
        return all_docs

    all_docs = asyncio.run(_fetch_all())
    total_found = len(all_docs)

    self.update_state(state="PROGRESS", meta={
        "stage": "deduplicating",
        "message": f"Found {total_found} articles. Deduplicating against local index...",
        "papers_found": total_found,
        "new_papers_indexed": 0,
        "triplets_ingested": 0
    })

    collection = init_literature_collection()
    dedup = LiteratureDeduplicator(collection=collection)
    chunker = get_chunker()

    newly_indexed = 0
    for doc in all_docs:
        if dedup.is_already_indexed(doc.doi, doc.title):
            continue

        chunks = chunker.split_text(f"{doc.title}\n\n{doc.summary}")
        if not chunks:
            continue

        base_meta = {
            "title": doc.title,
            "doi": doc.doi,
            "source": doc.source,
            "url": doc.url or "",
            "published_date": doc.published_date or "",
            "authors": ", ".join(doc.authors[:5]),
        }
        process_and_upsert(collection, chunks, base_metadata=base_meta, doi=doc.doi)
        newly_indexed += 1

    self.update_state(state="PROGRESS", meta={
        "stage": "extracting_triplets",
        "message": f"Indexed {newly_indexed} new articles into ChromaDB. Mining Neo4j chemical triplets...",
        "papers_found": total_found,
        "new_papers_indexed": newly_indexed,
        "triplets_ingested": 0
    })

    # Trigger graph extraction task if new chunks exist
    if newly_indexed > 0:
        process_chroma_chunks_task.delay()

    return {
        "status": "Complete",
        "query": query,
        "sources": active_sources,
        "papers_found": total_found,
        "new_papers_indexed": newly_indexed,
        "message": f"Successfully synced {newly_indexed} new documents from {', '.join(active_sources)}."
    }


@celery_app.task(bind=True, name="periodic_nightly_harvest")
def periodic_nightly_harvest(self):
    """
    Strategy 1: Autonomous Scheduled Harvester.
    Sweeps latest battery research topics off-peak.
    """
    topics = [
        "lithium-ion cathode degradation mechanisms",
        "solid-state electrolyte dendrite suppression",
        "cobalt-free high capacity cathode materials",
        "silicon anode solid electrolyte interphase",
        "sodium-ion battery cathode novel dopants"
    ]
    results = []
    for topic in topics:
        try:
            res = harvest_and_ingest_task(topic, sources=["arxiv", "crossref", "pubmed"], max_results=5)
            results.append(res)
        except Exception as e:
            logger.error(f"Error in nightly harvest for topic '{topic}': {e}")
    return {"status": "Complete", "topics_processed": len(results)}
