from app.core.celery_app import celery_app
from app.agents.workflow import app_graph
from app.agents.state import init_research_state
import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.chroma_client import init_literature_collection
from app.services.graph.extractor import extract_triplets_from_text
from app.services.graph.ingestion import ingest_triplets

logger = logging.getLogger(__name__)

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

    last_state = asyncio.run(_run())
    return {
        "status": "success",
        "generation": last_state.get("current_generation", 0),
        "results": last_state.get("best_candidates", []),
        "executive_summary": last_state.get("final_summary", ""),
        "generation_history": last_state.get("generation_history", []),
    }
