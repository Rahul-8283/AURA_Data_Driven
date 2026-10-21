import asyncio
import logging
import uuid
from typing import List, Literal
from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.security import get_current_user
from app.db.chroma_client import init_literature_collection
from app.db.neo4j_client import neo4j_conn
from app.services.harvesters import HARVESTER_SOURCES
from worker.tasks import harvest_and_ingest_task

logger = logging.getLogger(__name__)

# Every ingestion route writes to or reads from the shared knowledge base, so all require a signed-in user.
router = APIRouter(dependencies=[Depends(get_current_user)])

class IngestionSyncRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200, description="Target battery research topic to harvest")
    sources: List[Literal["arxiv", "wikipedia", "crossref", "pubmed", "all"]] = Field(
        default_factory=lambda: ["all"],
        min_length=1,
        description="Sources to query: arxiv, wikipedia, crossref, pubmed, or all"
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Max results per source")

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("query must contain at least 2 characters")
        return value

@router.post("/sync", status_code=202)
async def trigger_literature_sync(request: IngestionSyncRequest):
    """
    Trigger an asynchronous harvesting & ingestion run across chosen
    literature sources. Runs out-of-band in Celery without blocking user requests.
    """
    task_id = str(uuid.uuid4())
    sources = list(HARVESTER_SOURCES) if "all" in request.sources else list(dict.fromkeys(request.sources))

    task = harvest_and_ingest_task.apply_async(
        args=[request.query, sources, request.max_results],
        task_id=task_id
    )
    return {
        "task_id": task.id,
        "status": "started",
        "query": request.query,
        "sources": sources,
        "message": "Harvesting task initiated in background worker."
    }

@router.get("/status/{task_id}")
async def get_sync_status(task_id: str):
    """
    Poll the live state of an ingestion task (a harvest run, or the triplet extraction it queued).
    """
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == "PENDING":
        return {
            "status": "Pending",
            "stage": "queued",
            "message": "Task is queued in background worker...",
            "papers_found": 0,
            "new_papers_indexed": 0,
        }
    elif task_result.state == "PROGRESS":
        meta = task_result.info or {}
        return {
            "status": "In Progress",
            "stage": meta.get("stage", "harvesting"),
            "message": meta.get("message", "Processing literature..."),
            "papers_found": meta.get("papers_found", 0),
            "new_papers_indexed": meta.get("new_papers_indexed", 0),
            "triplets_ingested": meta.get("triplets_ingested", 0),
        }
    elif task_result.state == "SUCCESS":
        result = task_result.result or {}
        return {
            "status": "Complete",
            "stage": "complete",
            "message": result.get("message", "Harvesting complete."),
            "query": result.get("query", ""),
            "sources": result.get("sources", []),
            "papers_found": result.get("papers_found", 0),
            "new_papers_indexed": result.get("new_papers_indexed", 0),
            "source_errors": result.get("source_errors", {}),
            "extraction_task_id": result.get("extraction_task_id"),
            "chunks_extracted": result.get("chunks_extracted"),
            "chunks_pending": result.get("chunks_pending"),
            "triplets_ingested": result.get("triplets_ingested"),
            "stopped_reason": result.get("stopped_reason"),
        }
    elif task_result.state == "FAILURE":
        return {
            "status": "Failed",
            "stage": "failed",
            "message": "Harvesting task encountered an error.",
            "error": str(task_result.info)
        }
    else:
        return {"status": task_result.state}

def _count(session, query: str):
    record = session.run(query).single()
    return record["cnt"] if record else 0

def _collect_stats() -> dict:
    """Blocking database calls; run in a worker thread. A store that cannot be reached is
    reported as null with an entry in `errors`, never as a misleading zero."""
    stats = {"chroma_literature_chunks": None, "neo4j_nodes": None, "neo4j_relationships": None}
    errors = {}

    try:
        stats["chroma_literature_chunks"] = init_literature_collection().count()
    except Exception:
        logger.exception("Could not read ChromaDB statistics")
        errors["chroma"] = "unavailable"

    try:
        with neo4j_conn.get_session() as session:
            stats["neo4j_nodes"] = _count(session, "MATCH (n) RETURN count(n) AS cnt")
            stats["neo4j_relationships"] = _count(session, "MATCH ()-[r]->() RETURN count(r) AS cnt")
    except Exception:
        logger.exception("Could not read Neo4j statistics")
        errors["neo4j"] = "unavailable"

    return {**stats, "errors": errors}

@router.get("/stats")
async def get_knowledge_stats():
    """
    High-level statistics for the ChromaDB vectors and Neo4j knowledge graph.
    """
    stats = await asyncio.to_thread(_collect_stats)
    return {
        **stats,
        "supported_sources": ["arXiv", "Wikipedia", "Crossref", "PubMed (NCBI)"],
        "nightly_sweep_enabled": settings.NIGHTLY_HARVEST_ENABLED,
    }
